import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/webmasters']

def get_credentials():
    """Gets valid user credentials from storage."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds

def get_search_analytics(service, site_url, days=7):
    """Fetches search analytics data from GSC with multiple dimensions."""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Query data with multiple dimensions
    dimensions = ['query', 'device', 'country']
    request = {
        'startDate': start_date.isoformat(),
        'endDate': end_date.isoformat(),
        'dimensions': dimensions,
        'rowLimit': 1000  # Increased limit for better analysis
    }
    
    response = service.searchanalytics().query(
        siteUrl=site_url,
        body=request
    ).execute()
    
    return response.get('rows', []), start_date, end_date

def generate_visualizations(queries, output_dir='gsc_visualizations'):
    """Generates visualizations from the query data."""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Device Distribution
    device_data = defaultdict(lambda: {'clicks': 0, 'impressions': 0})
    for query in queries:
        device = query['keys'][1]  # device is the second dimension
        device_data[device]['clicks'] += query['clicks']
        device_data[device]['impressions'] += query['impressions']
    
    plt.figure(figsize=(10, 6))
    devices = list(device_data.keys())
    clicks = [device_data[d]['clicks'] for d in devices]
    plt.bar(devices, clicks)
    plt.title('Clicks by Device Type')
    plt.ylabel('Number of Clicks')
    plt.savefig(f'{output_dir}/device_distribution.png')
    plt.close()
    
    # 2. Top Countries
    country_data = defaultdict(lambda: {'clicks': 0, 'impressions': 0})
    for query in queries:
        country = query['keys'][2]  # country is the third dimension
        country_data[country]['clicks'] += query['clicks']
        country_data[country]['impressions'] += query['impressions']
    
    # Get top 5 countries by clicks
    top_countries = sorted(country_data.items(), 
                          key=lambda x: x[1]['clicks'], 
                          reverse=True)[:5]
    
    plt.figure(figsize=(12, 6))
    countries = [c[0] for c in top_countries]
    clicks = [c[1]['clicks'] for c in top_countries]
    plt.bar(countries, clicks)
    plt.title('Top 5 Countries by Clicks')
    plt.ylabel('Number of Clicks')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/top_countries.png')
    plt.close()
    
    # 3. CTR by Position
    position_data = defaultdict(lambda: {'clicks': 0, 'impressions': 0})
    for query in queries:
        position = round(query['position'])
        position_data[position]['clicks'] += query['clicks']
        position_data[position]['impressions'] += query['impressions']
    
    positions = sorted(position_data.keys())
    ctr = [position_data[p]['clicks'] / position_data[p]['impressions'] 
           if position_data[p]['impressions'] > 0 else 0 
           for p in positions]
    
    plt.figure(figsize=(10, 6))
    plt.plot(positions, ctr, marker='o')
    plt.title('CTR by Average Position')
    plt.xlabel('Average Position')
    plt.ylabel('Click-Through Rate')
    plt.grid(True)
    plt.savefig(f'{output_dir}/ctr_by_position.png')
    plt.close()
    
    return {
        'device_distribution': device_data,
        'country_distribution': country_data,
        'position_analysis': position_data
    }

def generate_insights(queries, visualizations):
    """Generates insights based on the query data and visualizations."""
    insights = []
    
    # Branded search analysis
    branded_queries = [q for q in queries if 'solstice' in q['keys'][0].lower()]
    if branded_queries:
        top_branded = max(branded_queries, key=lambda x: x['clicks'])
        insights.append({
            'title': 'Branded Search Performance',
            'points': [
                f'"{top_branded["keys"][0]}" is your top performing query',
                f'Strong CTR of {top_branded["ctr"]:.2%} indicates good relevance',
                f'Excellent average position of {top_branded["position"]:.1f}'
            ]
        })
    
    # Device analysis
    device_data = visualizations['device_distribution']
    top_device = max(device_data.items(), key=lambda x: x[1]['clicks'])
    insights.append({
        'title': 'Device Performance',
        'points': [
            f'Top performing device: {top_device[0]} with {top_device[1]["clicks"]} clicks',
            f'Mobile devices account for {device_data.get("MOBILE", {}).get("clicks", 0)} clicks',
            f'Desktop devices account for {device_data.get("DESKTOP", {}).get("clicks", 0)} clicks'
        ]
    })
    
    # Country analysis
    country_data = visualizations['country_distribution']
    top_country = max(country_data.items(), key=lambda x: x[1]['clicks'])
    insights.append({
        'title': 'Geographic Performance',
        'points': [
            f'Top performing country: {top_country[0]} with {top_country[1]["clicks"]} clicks',
            f'Total countries with traffic: {len(country_data)}',
            f'International reach: {sum(1 for c in country_data if c != "USA")} countries outside USA'
        ]
    })
    
    # Position analysis
    position_data = visualizations['position_analysis']
    top_positions = {p: d for p, d in position_data.items() if p <= 10}
    if top_positions:
        total_clicks_top10 = sum(d['clicks'] for d in top_positions.values())
        insights.append({
            'title': 'Position Analysis',
            'points': [
                f'Total clicks in top 10 positions: {total_clicks_top10}',
                f'Best performing position: {max(top_positions.items(), key=lambda x: x[1]["clicks"])[0]}',
                f'Average CTR for top 10 positions: {sum(d["clicks"] for d in top_positions.values()) / sum(d["impressions"] for d in top_positions.values()):.2%}'
            ]
        })
    
    return insights

def generate_recommendations(queries, visualizations):
    """Generates recommendations based on the query data and visualizations."""
    recommendations = []
    
    # Device-specific recommendations
    device_data = visualizations['device_distribution']
    if device_data.get('MOBILE', {}).get('clicks', 0) < device_data.get('DESKTOP', {}).get('clicks', 0):
        recommendations.append({
            'title': 'Mobile Optimization',
            'points': [
                'Improve mobile user experience',
                'Optimize for mobile-first indexing',
                'Ensure mobile page speed is optimal'
            ]
        })
    
    # Country-specific recommendations
    country_data = visualizations['country_distribution']
    if len(country_data) > 1:
        recommendations.append({
            'title': 'International SEO',
            'points': [
                'Create country-specific content',
                'Implement hreflang tags for international targeting',
                'Optimize for local search in top performing countries'
            ]
        })
    
    # Position-based recommendations
    position_data = visualizations['position_analysis']
    high_impression_positions = {p: d for p, d in position_data.items() 
                               if d['impressions'] > 0 and d['clicks'] == 0}
    if high_impression_positions:
        recommendations.append({
            'title': 'SERP Optimization',
            'points': [
                'Improve meta descriptions for high-impression positions',
                'Enhance rich snippets for better CTR',
                'Optimize title tags for better click-through rates'
            ]
        })
    
    return recommendations

def generate_markdown_report(queries, start_date, end_date, insights, recommendations):
    """Generates a markdown formatted report with visualizations."""
    report = f"""# Google Search Console Performance Report

## Search Performance Overview
**Time Period:** {start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}

### Top Performing Queries
| Query | Clicks | Impressions | CTR | Avg. Position |
|-------|--------|-------------|-----|---------------|
"""
    
    # Add query data
    for query in queries[:5]:  # Show top 5 queries
        report += f"| {query['keys'][0]} | {query['clicks']} | {query['impressions']} | {query['ctr']:.2%} | {query['position']:.1f} |\n"
    
    # Add visualizations
    report += "\n### Performance Visualizations\n"
    report += "![Device Distribution](gsc_visualizations/device_distribution.png)\n"
    report += "![Top Countries](gsc_visualizations/top_countries.png)\n"
    report += "![CTR by Position](gsc_visualizations/ctr_by_position.png)\n"
    
    # Add insights
    report += "\n### Key Insights\n"
    for i, insight in enumerate(insights, 1):
        report += f"{i}. **{insight['title']}**\n"
        for point in insight['points']:
            report += f"   - {point}\n"
    
    # Add recommendations
    report += "\n### Recommendations\n"
    for i, rec in enumerate(recommendations, 1):
        report += f"{i}. **{rec['title']}**\n"
        for point in rec['points']:
            report += f"   - {point}\n"
    
    report += "\n---\n*Data sourced from Google Search Console API*"
    
    return report

def main():
    """Main function to generate the GSC report."""
    try:
        # Get credentials and build service
        creds = get_credentials()
        service = build('searchconsole', 'v1', credentials=creds)
        
        # Get site list
        sites = service.sites().list().execute()
        if not sites.get('siteEntry'):
            print("No sites found in GSC account")
            return
        
        # Use the first site
        site_url = sites['siteEntry'][0]['siteUrl']
        print(f"Generating report for: {site_url}")
        
        # Get search analytics data
        queries, start_date, end_date = get_search_analytics(service, site_url)
        
        if not queries:
            print("No search data available for the selected period")
            return
        
        # Generate visualizations
        print("Generating visualizations...")
        visualizations = generate_visualizations(queries)
        
        # Generate insights and recommendations
        insights = generate_insights(queries, visualizations)
        recommendations = generate_recommendations(queries, visualizations)
        
        # Generate and save the report
        report = generate_markdown_report(queries, start_date, end_date, 
                                       insights, recommendations)
        
        # Save to file
        output_file = f"gsc_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(output_file, 'w') as f:
            f.write(report)
        
        print(f"\n✅ Report generated successfully: {output_file}")
        print("📊 Visualizations saved in 'gsc_visualizations' directory")
        
    except Exception as e:
        print(f"\n❌ Error generating report: {str(e)}")

if __name__ == '__main__':
    main() 