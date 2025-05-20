#!/usr/bin/env python3

import schedule
import time
import subprocess
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler()
    ]
)

# Configuration
DOMAINS = [
    "solstice-recovery.com",
    "score-systems.com",
    "myrtlebeachhouse111.com"
]
GOOGLE_CLOUD_PROJECT = "YOUR_PROJECT_ID"  # Replace with your project ID
BIGQUERY_DATASET = "site_analysis"  # Replace with your dataset ID

def run_analysis(domain):
    """Run site analysis and export data for a domain"""
    try:
        logging.info(f"Starting analysis for {domain}")
        
        # Run site analyzer
        analyzer_cmd = f"python site_analyzer.py https://{domain}/"
        subprocess.run(analyzer_cmd, shell=True, check=True)
        
        # Run site reporter
        reporter_cmd = f"python site_reporter.py {domain} --google-doc"
        subprocess.run(reporter_cmd, shell=True, check=True)
        
        # Export to BigQuery
        analysis_file = f"{domain}-analysis-report.json"
        if os.path.exists(analysis_file):
            exporter_cmd = f"python data_exporter.py {analysis_file} --project-id {GOOGLE_CLOUD_PROJECT} --dataset-id {BIGQUERY_DATASET}"
            subprocess.run(exporter_cmd, shell=True, check=True)
            logging.info(f"Successfully completed analysis and export for {domain}")
        else:
            logging.error(f"Analysis file not found for {domain}")
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Error processing {domain}: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error for {domain}: {str(e)}")

def run_all_analyses():
    """Run analysis for all configured domains"""
    logging.info("Starting scheduled analysis run")
    for domain in DOMAINS:
        run_analysis(domain)
    logging.info("Completed scheduled analysis run")

def main():
    # Schedule daily run at 2 AM
    schedule.every().day.at("02:00").do(run_all_analyses)
    
    logging.info("Automation service started")
    logging.info(f"Monitoring {len(DOMAINS)} domains: {', '.join(DOMAINS)}")
    
    # Run immediately on startup
    run_all_analyses()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main() 