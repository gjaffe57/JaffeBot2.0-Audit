#!/usr/bin/env python3

from google.cloud import bigquery
from datetime import datetime
import json
import pandas as pd
import os
import argparse

class SiteAnalysisExporter:
    def __init__(self, project_id, dataset_id):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)
        
    def prepare_metrics_table(self, analysis_data):
        """Prepare metrics data for BigQuery"""
        metrics = {
            'timestamp': datetime.now(),
            'domain': analysis_data['summary']['domain'],
            'technical_score': analysis_data['scores']['technical'],
            'seo_score': analysis_data['scores']['seo'],
            'content_score': analysis_data['scores']['content'],
            'mobile_score': analysis_data['scores']['mobile'],
            'overall_score': analysis_data['scores']['overall'],
            'total_issues': analysis_data['summary']['total_issues'],
            'critical_issues': analysis_data['summary']['critical_issues']
        }
        return pd.DataFrame([metrics])

    def prepare_issues_table(self, analysis_data):
        """Prepare issues data for BigQuery"""
        issues = []
        for issue in analysis_data['technical_issues'] + \
                    analysis_data['seo_issues'] + \
                    analysis_data['content_issues']:
            issues.append({
                'timestamp': datetime.now(),
                'domain': analysis_data['summary']['domain'],
                'issue_type': issue['type'],
                'description': issue['description'],
                'impact': issue['impact'],
                'priority': issue['priority']
            })
        return pd.DataFrame(issues)

    def prepare_recommendations_table(self, analysis_data):
        """Prepare recommendations data for BigQuery"""
        recommendations = []
        for rec in analysis_data['recommendations']:
            recommendations.append({
                'timestamp': datetime.now(),
                'domain': analysis_data['summary']['domain'],
                'category': rec['category'],
                'action': rec['action'],
                'priority': rec['priority'],
                'impact': rec['impact'],
                'estimated_effort': rec['estimated_effort'],
                'implementation_steps': json.dumps(rec['implementation_steps'])
            })
        return pd.DataFrame(recommendations)

    def create_tables_if_not_exist(self):
        """Create BigQuery tables if they don't exist"""
        dataset_ref = self.client.dataset(self.dataset_id)
        
        # Define table schemas
        metrics_schema = [
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("domain", "STRING"),
            bigquery.SchemaField("technical_score", "INTEGER"),
            bigquery.SchemaField("seo_score", "INTEGER"),
            bigquery.SchemaField("content_score", "INTEGER"),
            bigquery.SchemaField("mobile_score", "INTEGER"),
            bigquery.SchemaField("overall_score", "INTEGER"),
            bigquery.SchemaField("total_issues", "INTEGER"),
            bigquery.SchemaField("critical_issues", "INTEGER")
        ]

        issues_schema = [
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("domain", "STRING"),
            bigquery.SchemaField("issue_type", "STRING"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("impact", "STRING"),
            bigquery.SchemaField("priority", "STRING")
        ]

        recommendations_schema = [
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("domain", "STRING"),
            bigquery.SchemaField("category", "STRING"),
            bigquery.SchemaField("action", "STRING"),
            bigquery.SchemaField("priority", "STRING"),
            bigquery.SchemaField("impact", "STRING"),
            bigquery.SchemaField("estimated_effort", "STRING"),
            bigquery.SchemaField("implementation_steps", "STRING")
        ]

        # Create tables
        tables = {
            'site_metrics': metrics_schema,
            'site_issues': issues_schema,
            'site_recommendations': recommendations_schema
        }

        for table_name, schema in tables.items():
            table_ref = dataset_ref.table(table_name)
            try:
                self.client.get_table(table_ref)
                print(f"Table {table_name} already exists")
            except Exception:
                table = bigquery.Table(table_ref, schema=schema)
                self.client.create_table(table)
                print(f"Created table {table_name}")

    def export_to_bigquery(self, analysis_file):
        """Export analysis data to BigQuery"""
        try:
            with open(analysis_file, 'r') as f:
                analysis_data = json.load(f)

            # Create tables if they don't exist
            self.create_tables_if_not_exist()

            # Prepare dataframes
            metrics_df = self.prepare_metrics_table(analysis_data)
            issues_df = self.prepare_issues_table(analysis_data)
            recommendations_df = self.prepare_recommendations_table(analysis_data)

            # Upload data
            tables = {
                'site_metrics': metrics_df,
                'site_issues': issues_df,
                'site_recommendations': recommendations_df
            }

            for table_name, df in tables.items():
                table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
                job_config = bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND
                )
                
                job = self.client.load_table_from_dataframe(
                    df, table_id, job_config=job_config
                )
                job.result()  # Wait for the job to complete
                
                print(f"Uploaded {len(df)} rows to {table_name}")
            
            return True
        except Exception as e:
            print(f"Error exporting data: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Export site analysis data to BigQuery")
    parser.add_argument("analysis_file", help="Path to the analysis JSON file")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    parser.add_argument("--dataset-id", required=True, help="BigQuery dataset ID")
    
    args = parser.parse_args()
    
    exporter = SiteAnalysisExporter(args.project_id, args.dataset_id)
    success = exporter.export_to_bigquery(args.analysis_file)
    
    if success:
        print("Data export completed successfully")
    else:
        print("Data export failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 