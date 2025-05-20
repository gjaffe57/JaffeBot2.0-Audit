#!/usr/bin/env python3

import json
import os
import sys
from typing import Dict, List, Any
from datetime import datetime
import argparse
from pathlib import Path
from utils.google_docs import GoogleDocsManager

class SiteReporter:
    def __init__(self, domain: str):
        self.domain = domain
        self.issues_file = f"{domain}-issues.json"
        self.page_info_file = f"{domain}-page-info.json"
        self.technical_file = f"{domain}-technical-discovery.json"
        
        # Load data
        self.issues = self._load_json(self.issues_file)
        self.page_info = self._load_json(self.page_info_file)
        self.technical = self._load_json(self.technical_file)
        
        # Initialize report sections
        self.report = {
            "summary": {},
            "technical_issues": [],
            "seo_issues": [],
            "content_issues": [],
            "recommendations": [],
            "scores": {
                "overall": 0,
                "technical": 0,
                "seo": 0,
                "content": 0,
                "mobile": 0
            }
        }
        
        # Initialize Google Docs manager
        self.docs_manager = GoogleDocsManager()

    def _load_json(self, filename: str) -> Dict:
        """Load and parse a JSON file."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {filename} not found")
            return {}
        except json.JSONDecodeError:
            print(f"Error: {filename} contains invalid JSON")
            return {}

    def _calculate_technical_score(self) -> int:
        """Calculate technical performance score (0-100)."""
        score = 100
        
        if self.technical.get("performance_metrics"):
            metrics = self.technical["performance_metrics"]
            # Deduct points for slow load time
            if metrics.get("load_time", 0) > 3:
                score -= 20
            # Deduct points for too many resources
            if metrics.get("resource_count", 0) > 50:
                score -= 15
            # Deduct points for large page size
            if metrics.get("total_size", 0) > 5000000:  # 5MB
                score -= 15
        
        # Deduct points for critical issues
        if self.technical.get("critical_issues"):
            score -= min(30, len(self.technical["critical_issues"]) * 10)
        
        # Deduct points for security issues
        if self.technical.get("security_issues"):
            score -= min(20, len(self.technical["security_issues"]) * 5)
        
        return max(0, score)

    def _calculate_seo_score(self) -> int:
        """Calculate SEO optimization score (0-100)."""
        score = 100
        
        if self.page_info.get("meta"):
            meta = self.page_info["meta"]
            # Check meta title
            if not meta.get("title"):
                score -= 20
            elif len(meta["title"]) < 30 or len(meta["title"]) > 60:
                score -= 10
            
            # Check meta description
            if not meta.get("description"):
                score -= 15
            elif len(meta["description"]) < 120 or len(meta["description"]) > 160:
                score -= 10
            
            # Check social media tags
            social_tags = ["og:title", "og:description", "og:image", "twitter:card"]
            missing_social = sum(1 for tag in social_tags if not meta.get(tag))
            score -= missing_social * 5
        
        # Check for broken links
        if self.technical.get("broken_links"):
            score -= min(15, len(self.technical["broken_links"]) * 3)
        
        # Check for schema markup
        if self.technical.get("structured_data"):
            structured_data = self.technical["structured_data"]
            if structured_data["page_coverage"]["pages_with_schema"] == 0:
                score -= 15
            elif structured_data["page_coverage"]["pages_with_schema"] < structured_data["page_coverage"]["total_pages"] * 0.5:
                score -= 10
        
        return max(0, score)

    def _calculate_content_score(self) -> int:
        """Calculate content quality score (0-100)."""
        score = 100
        
        if self.page_info.get("content"):
            content = self.page_info["content"]
            
            # Check content length
            if content.get("text_length", 0) < 300:
                score -= 20
            
            # Check heading structure
            if not content.get("headings"):
                score -= 15
            else:
                heading_structure = content["headings"]
                if not any(h.get("level") == 1 for h in heading_structure):
                    score -= 10
            
            # Check for images
            if not content.get("images"):
                score -= 10
            
            # Check for links
            if not content.get("links"):
                score -= 10
            
            # Check readability
            if content.get("text_length", 0) > 0:
                readability = self._calculate_readability(content)
                score = min(score, readability)
        
        return max(0, score)

    def _calculate_mobile_score(self) -> int:
        """Calculate mobile responsiveness score (0-100)."""
        score = 100
        
        # Check viewport meta tag
        if not self.technical.get("viewport_meta", {}).get("present"):
            score -= 20
        
        # Check responsive images
        if self.page_info.get("content", {}).get("images"):
            responsive_images = sum(1 for img in self.page_info["content"]["images"] 
                                 if img.get("responsive"))
            total_images = len(self.page_info["content"]["images"])
            if total_images > 0:
                score -= (total_images - responsive_images) * 5
        
        # Check media queries
        if not self.technical.get("media_queries", {}).get("present"):
            score -= 15
        
        return max(0, score)

    def _calculate_readability(self, content: Dict) -> int:
        """Calculate content readability score (0-100)."""
        score = 100
        
        # Penalize for very short content
        if content.get("text_length", 0) < 300:
            score -= 20
        
        # Penalize for lack of structure
        if not content.get("headings"):
            score -= 15
        
        # Penalize for lack of media
        if not content.get("images"):
            score -= 10
        
        # Penalize for lack of links
        if not content.get("links"):
            score -= 10
        
        return max(0, score)

    def analyze_technical_issues(self) -> List[Dict]:
        """Analyze technical issues from the site."""
        issues = []
        
        # Check for critical technical issues
        if self.technical.get("critical_issues"):
            for issue in self.technical["critical_issues"]:
                issues.append({
                    "type": "critical",
                    "description": issue,
                    "impact": "High",
                    "priority": "Immediate"
                })

        # Check for performance issues
        if self.technical.get("performance_metrics"):
            metrics = self.technical["performance_metrics"]
            if metrics.get("load_time", 0) > 3:
                issues.append({
                    "type": "performance",
                    "description": f"Slow page load time: {metrics['load_time']}s",
                    "impact": "Medium",
                    "priority": "High",
                    "metrics": {
                        "load_time": metrics.get("load_time", 0),
                        "resource_count": metrics.get("resource_count", 0),
                        "total_size": metrics.get("total_size", 0)
                    }
                })

        # Check for security issues
        if self.technical.get("security_issues"):
            for issue in self.technical["security_issues"]:
                issues.append({
                    "type": "security",
                    "description": issue,
                    "impact": "High",
                    "priority": "Immediate"
                })

        # Add mobile responsiveness check
        if self.technical.get("viewport_meta"):
            if not self.technical["viewport_meta"].get("present"):
                issues.append({
                    "type": "mobile",
                    "description": "Missing viewport meta tag for mobile responsiveness",
                    "impact": "High",
                    "priority": "High"
                })

        return issues

    def analyze_seo_issues(self) -> List[Dict]:
        """Analyze SEO-related issues."""
        issues = []
        
        # Check meta information
        if self.page_info.get("meta"):
            meta = self.page_info["meta"]
            if not meta.get("title"):
                issues.append({
                    "type": "meta",
                    "description": "Missing page title",
                    "impact": "High",
                    "priority": "High"
                })
            elif len(meta["title"]) < 30 or len(meta["title"]) > 60:
                issues.append({
                    "type": "meta",
                    "description": f"Title length ({len(meta['title'])}) should be between 30-60 characters",
                    "impact": "Medium",
                    "priority": "Medium"
                })
            
            if not meta.get("description"):
                issues.append({
                    "type": "meta",
                    "description": "Missing meta description",
                    "impact": "Medium",
                    "priority": "Medium"
                })
            elif len(meta["description"]) < 120 or len(meta["description"]) > 160:
                issues.append({
                    "type": "meta",
                    "description": f"Description length ({len(meta['description'])}) should be between 120-160 characters",
                    "impact": "Medium",
                    "priority": "Medium"
                })

        # Check for broken links
        if self.technical.get("broken_links"):
            issues.append({
                "type": "links",
                "description": f"Found {len(self.technical['broken_links'])} broken links",
                "impact": "Medium",
                "priority": "High",
                "broken_links": self.technical["broken_links"]
            })

        # Add social media optimization check
        if self.page_info.get("meta"):
            meta = self.page_info["meta"]
            social_meta = {
                "og:title": meta.get("og:title"),
                "og:description": meta.get("og:description"),
                "og:image": meta.get("og:image"),
                "twitter:card": meta.get("twitter:card")
            }
            
            missing_social = [k for k, v in social_meta.items() if not v]
            if missing_social:
                issues.append({
                    "type": "social",
                    "description": f"Missing social media meta tags: {', '.join(missing_social)}",
                    "impact": "Medium",
                    "priority": "Medium"
                })

        return issues

    def analyze_content_issues(self) -> List[Dict]:
        """Analyze content-related issues."""
        issues = []
        
        # Check content structure
        if self.page_info.get("content"):
            content = self.page_info["content"]
            
            # Heading structure analysis
            if not content.get("headings"):
                issues.append({
                    "type": "structure",
                    "description": "No heading structure found",
                    "impact": "Medium",
                    "priority": "Medium"
                })
            else:
                heading_structure = content["headings"]
                if not any(h.get("level") == 1 for h in heading_structure):
                    issues.append({
                        "type": "structure",
                        "description": "Missing H1 heading",
                        "impact": "High",
                        "priority": "High"
                    })
                
                # Check heading hierarchy
                levels = [h.get("level", 0) for h in heading_structure]
                if levels and max(levels) - min(levels) > 2:
                    issues.append({
                        "type": "structure",
                        "description": "Irregular heading hierarchy detected",
                        "impact": "Medium",
                        "priority": "Medium"
                    })
            
            # Content length and quality analysis
            text_length = content.get("text_length", 0)
            if text_length < 300:
                issues.append({
                    "type": "content",
                    "description": "Content length is too short",
                    "impact": "Medium",
                    "priority": "Medium"
                })
            
            # Add content quality metrics
            content_metrics = {
                "word_count": text_length,
                "paragraphs": len(content.get("paragraphs", [])),
                "images": len(content.get("images", [])),
                "links": len(content.get("links", [])),
                "readability_score": self._calculate_readability(content)
            }
            # Add Flesch-Kincaid if available
            if "flesch_kincaid_grade" in content:
                content_metrics["flesch_kincaid_grade"] = content["flesch_kincaid_grade"]
            
            issues.append({
                "type": "content_metrics",
                "description": "Content quality metrics",
                "impact": "Medium",
                "priority": "Medium",
                "metrics": content_metrics
            })

        return issues

    def generate_recommendations(self) -> List[Dict]:
        """Generate actionable recommendations based on issues."""
        recommendations = []
        
        # Technical recommendations
        if self.report["technical_issues"]:
            recommendations.extend([
                {
                    "category": "Technical",
                    "action": "Fix critical technical issues",
                    "priority": "Immediate",
                    "impact": "High",
                    "estimated_effort": "High",
                    "implementation_steps": [
                        "Review critical issues list",
                        "Prioritize security-related fixes",
                        "Address performance bottlenecks"
                    ]
                },
                {
                    "category": "Technical",
                    "action": "Optimize page load time",
                    "priority": "High",
                    "impact": "Medium",
                    "estimated_effort": "Medium",
                    "implementation_steps": [
                        "Optimize image sizes",
                        "Minify CSS and JavaScript",
                        "Implement lazy loading",
                        "Consider using a CDN"
                    ]
                }
            ])

        # SEO recommendations
        if self.report["seo_issues"]:
            recommendations.extend([
                {
                    "category": "SEO",
                    "action": "Implement proper meta tags",
                    "priority": "High",
                    "impact": "High",
                    "estimated_effort": "Low",
                    "implementation_steps": [
                        "Add missing meta title",
                        "Add meta description",
                        "Implement social media meta tags"
                    ]
                },
                {
                    "category": "SEO",
                    "action": "Fix broken links",
                    "priority": "High",
                    "impact": "Medium",
                    "estimated_effort": "Medium",
                    "implementation_steps": [
                        "Review broken links list",
                        "Update or remove broken links",
                        "Implement 301 redirects where appropriate"
                    ]
                }
            ])

        # Content recommendations
        if self.report["content_issues"]:
            recommendations.extend([
                {
                    "category": "Content",
                    "action": "Improve content structure",
                    "priority": "Medium",
                    "impact": "Medium",
                    "estimated_effort": "Medium",
                    "implementation_steps": [
                        "Implement proper heading hierarchy",
                        "Ensure H1 tag is present",
                        "Organize content into logical sections"
                    ]
                },
                {
                    "category": "Content",
                    "action": "Enhance content quality",
                    "priority": "Medium",
                    "impact": "Medium",
                    "estimated_effort": "High",
                    "implementation_steps": [
                        "Expand content length",
                        "Add relevant images",
                        "Include internal and external links",
                        "Improve readability"
                    ]
                }
            ])

        return recommendations

    def generate_report(self) -> Dict:
        """Generate the complete site analysis report."""
        # Analyze different aspects
        self.report["technical_issues"] = self.analyze_technical_issues()
        self.report["seo_issues"] = self.analyze_seo_issues()
        self.report["content_issues"] = self.analyze_content_issues()
        
        # Calculate scores
        self.report["scores"] = {
            "technical": self._calculate_technical_score(),
            "seo": self._calculate_seo_score(),
            "content": self._calculate_content_score(),
            "mobile": self._calculate_mobile_score()
        }
        
        # Calculate overall score (weighted average)
        weights = {
            "technical": 0.3,
            "seo": 0.3,
            "content": 0.2,
            "mobile": 0.2
        }
        self.report["scores"]["overall"] = int(sum(
            self.report["scores"][category] * weight
            for category, weight in weights.items()
        ))
        
        # Generate recommendations
        self.report["recommendations"] = self.generate_recommendations()
        
        # Add summary with enhanced metrics
        self.report["summary"] = {
            "domain": self.domain,
            "analysis_date": datetime.now().isoformat(),
            "total_issues": len(self.report["technical_issues"] + 
                              self.report["seo_issues"] + 
                              self.report["content_issues"]),
            "critical_issues": len([i for i in self.report["technical_issues"] 
                                  if i["priority"] == "Immediate"]),
            "overall_score": self.report["scores"]["overall"],
            "priority_distribution": {
                "immediate": len([i for i in self.report["technical_issues"] + 
                                self.report["seo_issues"] + 
                                self.report["content_issues"] 
                                if i["priority"] == "Immediate"]),
                "high": len([i for i in self.report["technical_issues"] + 
                           self.report["seo_issues"] + 
                           self.report["content_issues"] 
                           if i["priority"] == "High"]),
                "medium": len([i for i in self.report["technical_issues"] + 
                             self.report["seo_issues"] + 
                             self.report["content_issues"] 
                             if i["priority"] == "Medium"])
            }
        }
        
        return self.report

    def save_report(self, output_file: str = None, create_google_doc: bool = False, share_with: str = None) -> None:
        """Save the report to a JSON file and optionally create a Google Doc.
        
        Args:
            output_file: Path to save the JSON report
            create_google_doc: Whether to create a Google Doc version
            share_with: Email address to share the Google Doc with
        """
        # Save JSON report
        if output_file is None:
            output_file = f"{self.domain}-analysis-report.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2)
        print(f"Report saved to {output_file}")
        
        # Create Google Doc if requested
        if create_google_doc:
            # Convert report to markdown format
            markdown_content = self._generate_markdown_report()
            
            # Create Google Doc
            doc_id = self.docs_manager.create_document(
                title=f"Website Analysis Report: {self.domain}",
                content=markdown_content
            )
            
            if doc_id:
                print(f"Google Doc created successfully. Document ID: {doc_id}")
                
                # Share document if email provided
                if share_with:
                    if self.docs_manager.share_document(doc_id, share_with):
                        print(f"Document shared with {share_with}")
                    else:
                        print("Failed to share document")
            else:
                print("Failed to create Google Doc")

    def _generate_markdown_report(self) -> str:
        """Generate a markdown formatted report."""
        report = []
        
        # Title
        report.append(f"# Website Analysis Report: {self.domain}\n")
        
        # Executive Summary
        report.append("## Executive Summary")
        report.append(f"The website has a strong overall health score of {self.report['scores']['overall']}/100, "
                     "indicating good overall performance and optimization. The site excels in technical aspects "
                     "and content quality, with some room for improvement in mobile responsiveness and SEO elements.\n")
        
        # Add GSC data section
        gsc_sections = self._add_gsc_data_to_report()
        if gsc_sections:
            report.extend(gsc_sections)
        
        # Detailed Scores
        report.append("## Detailed Scores")
        report.append("| Category | Score | Status | Explanation |")
        report.append("|----------|-------|---------|-------------|")
        
        status_map = {
            (90, 100): "Excellent",
            (80, 89): "Very Good",
            (70, 79): "Good",
            (60, 69): "Needs Improvement",
            (0, 59): "Poor"
        }
        
        def get_status(score):
            for (min_score, max_score), status in status_map.items():
                if min_score <= score <= max_score:
                    return status
            return "Unknown"
        
        # Add Content Overview section
        report.append("\n## Content Overview")
        
        # Calculate average Flesch-Kincaid score and find highest/lowest pages
        flesch_scores = []
        for url, info in self.page_info.items():
            if info.get("flesch_kincaid_grade") is not None:
                flesch_scores.append((url, info["flesch_kincaid_grade"]))
        
        if flesch_scores:
            avg_flesch = sum(score for _, score in flesch_scores) / len(flesch_scores)
            most_readable = min(flesch_scores, key=lambda x: x[1])  # Lowest grade = easiest
            least_readable = max(flesch_scores, key=lambda x: x[1]) # Highest grade = hardest
            
            report.append(f"### Overall Readability")
            report.append(f"- **Average Flesch-Kincaid Grade Level**: {avg_flesch:.1f}")
            report.append(f"- **Most Readable Page**: {most_readable[0]} (Grade Level: {most_readable[1]:.1f})")
            report.append(f"- **Least Readable Page**: {least_readable[0]} (Grade Level: {least_readable[1]:.1f})")
            report.append("\n**What does this mean?**\n")
            report.append("- The Flesch-Kincaid Grade Level estimates the U.S. school grade needed to easily read the text.\n- Lower grade levels = easier to read.\n- Example: 'Grade 8' means an eighth-grader should understand it.\n")
            report.append("\n**How is it calculated?**\n")
            report.append("- Shorter sentences and simpler words = easier (lower grade level).\n- Longer sentences and more complex words = harder.\n")
            report.append("\n**Recommendations:**\n")
            if avg_flesch > 12:
                report.append("- ⚠️ Content is relatively complex. Consider simplifying language and shortening sentences.")
            elif avg_flesch < 8:
                report.append("- ✅ Content is very accessible. Good for a general audience.")
            else:
                report.append("- ✅ Content is at an appropriate level for most audiences.")
        else:
            report.append("No readability scores available for analysis.")
        
        # Add Content Metrics Analysis
        report.append("\n### Content Metrics Analysis")
        
        # Calculate aggregate metrics across all pages
        total_pages = len(self.page_info)
        total_words = 0
        total_images = 0
        total_links = 0
        pages_with_headings = 0
        pages_with_h1 = 0
        
        for url, info in self.page_info.items():
            if info.get("content"):
                content = info["content"]
                total_words += content.get("text_length", 0)
                total_images += len(content.get("images", []))
                total_links += len(content.get("links", []))
                if content.get("headings"):
                    pages_with_headings += 1
                    if any(h.get("level") == 1 for h in content["headings"]):
                        pages_with_h1 += 1
        
        # Content Length Analysis
        avg_words = total_words / total_pages if total_pages > 0 else 0
        report.append("\n#### Content Length")
        report.append(f"- **Average Words per Page**: {avg_words:.0f}")
        if avg_words < 300:
            report.append("  - ⚠️ Content length is below recommended minimum of 300 words")
            report.append("  - Consider expanding content to provide more value to readers")
        elif avg_words > 2000:
            report.append("  - ✅ Content length is substantial")
            report.append("  - Consider breaking up very long content into multiple pages")
        else:
            report.append("  - ✅ Content length is within recommended range")
            report.append("  - Good balance between comprehensiveness and readability")
        
        # Content Structure Analysis
        heading_coverage = (pages_with_headings / total_pages * 100) if total_pages > 0 else 0
        h1_coverage = (pages_with_h1 / total_pages * 100) if total_pages > 0 else 0
        report.append("\n#### Content Structure")
        report.append(f"- **Pages with Headings**: {heading_coverage:.1f}%")
        report.append(f"- **Pages with H1 Tags**: {h1_coverage:.1f}%")
        if heading_coverage < 80:
            report.append("  - ⚠️ Many pages lack proper heading structure")
            report.append("  - Implement consistent heading hierarchy across all pages")
        else:
            report.append("  - ✅ Good heading structure implementation")
        if h1_coverage < 100:
            report.append("  - ⚠️ Some pages are missing H1 tags")
            report.append("  - Ensure every page has exactly one H1 tag")
        else:
            report.append("  - ✅ All pages have H1 tags")
        
        # Media Usage Analysis
        avg_images = total_images / total_pages if total_pages > 0 else 0
        avg_links = total_links / total_pages if total_pages > 0 else 0
        report.append("\n#### Media Usage")
        report.append(f"- **Average Images per Page**: {avg_images:.1f}")
        report.append(f"- **Average Links per Page**: {avg_links:.1f}")
        if avg_images < 1:
            report.append("  - ⚠️ Low image usage across pages")
            report.append("  - Consider adding relevant images to enhance content")
        elif avg_images > 10:
            report.append("  - ⚠️ High number of images per page")
            report.append("  - Consider optimizing image loading and reducing count if possible")
        else:
            report.append("  - ✅ Good balance of images per page")
        if avg_links < 3:
            report.append("  - ⚠️ Low number of links per page")
            report.append("  - Add more internal and external links to improve navigation")
        else:
            report.append("  - ✅ Good number of links per page")
        
        report.append("")
        
        # Technical Score Explanation
        tech_explanation = "Based on performance metrics, security, and critical issues. Deductions for slow load times, resource count, and security vulnerabilities."
        
        # SEO Score Explanation
        seo_explanation = "Evaluates meta tags, social media optimization, broken links, and schema markup implementation."
        
        # Content Score Explanation
        content_explanation = "Assesses content length, structure, media usage, and readability metrics."
        
        # Mobile Score Explanation
        mobile_explanation = "Measures mobile responsiveness through viewport settings, responsive images, and media queries."
        
        for category, score in self.report['scores'].items():
            if category != 'overall':
                explanation = {
                    'technical': tech_explanation,
                    'seo': seo_explanation,
                    'content': content_explanation,
                    'mobile': mobile_explanation
                }.get(category, "")
                report.append(f"| {category.title()} | {score}/100 | {get_status(score)} | {explanation} |")
        
        report.append(f"| Overall | {self.report['scores']['overall']}/100 | {get_status(self.report['scores']['overall'])} | Weighted average of all categories |\n")
        
        # Schema Markup Analysis
        if self.technical.get("structured_data"):
            report.append("## Schema Markup Analysis")
            structured_data = self.technical["structured_data"]
            report.append(f"- **Pages with Schema**: {structured_data['page_coverage']['pages_with_schema']} of {structured_data['page_coverage']['total_pages']}")
            report.append("- **Schema Types Found**:")
            for schema_type, implementations in structured_data["schema_types"].items():
                if implementations:
                    report.append(f"  - {schema_type}: {len(implementations)} implementations")
            report.append("- **Implementation Methods**:")
            for method, data in structured_data["implementation_methods"].items():
                report.append(f"  - {method.upper()}: {data['count']} implementations")
                if data['invalid']:
                    report.append(f"    - Invalid implementations: {len(data['invalid'])}")
            report.append("")
        
        # Issues Overview
        report.append("## Issues Overview")
        report.append(f"- **Total Issues Found**: {self.report['summary']['total_issues']}")
        report.append(f"- **Critical Issues**: {self.report['summary']['critical_issues']}")
        report.append("- **Priority Distribution**:")
        for priority, count in self.report['summary']['priority_distribution'].items():
            report.append(f"  - {priority.title()}: {count}")
        report.append("")
        
        # Main Issues
        if self.report['technical_issues'] or self.report['seo_issues'] or self.report['content_issues']:
            report.append("## Main Issues Identified")
            
            for category in ['technical_issues', 'seo_issues', 'content_issues']:
                if self.report[category]:
                    report.append(f"### {category.replace('_', ' ').title()}")
                    for issue in self.report[category]:
                        report.append(f"- **{issue['type'].title()}**: {issue['description']}")
                        report.append(f"  - Impact: {issue['impact']}")
                        report.append(f"  - Priority: {issue['priority']}")
                        if 'metrics' in issue:
                            report.append("  - Metrics:")
                            for key, value in issue['metrics'].items():
                                report.append(f"    - {key}: {value}")
                            # If Flesch-Kincaid is present, add a brief explanation
                            if 'flesch_kincaid_grade' in issue['metrics']:
                                report.append(f"    - Flesch-Kincaid Grade: {issue['metrics']['flesch_kincaid_grade']} (U.S. school grade level; lower is easier to read)")
                    report.append("")
        
        # Recommendations
        if self.report['recommendations']:
            report.append("## Recommendations")
            for rec in self.report['recommendations']:
                report.append(f"### {rec['category']} - {rec['action']}")
                report.append(f"- Priority: {rec['priority']}")
                report.append(f"- Impact: {rec['impact']}")
                report.append(f"- Estimated Effort: {rec['estimated_effort']}")
                report.append("- Implementation Steps:")
                for step in rec['implementation_steps']:
                    report.append(f"  - {step}")
                report.append("")
        
        # Next Steps
        report.append("## Next Steps")
        report.append("1. Address critical issues first")
        report.append("2. Implement high-priority recommendations")
        report.append("3. Monitor improvements and track metrics")
        report.append("4. Regular maintenance and updates")
        report.append("")
        
        # Footer
        report.append("---")
        report.append(f"*Report generated on: {self.report['summary']['analysis_date']}*")
        
        return "\n".join(report)

    def _add_gsc_data_to_report(self) -> List[str]:
        """Add Google Search Console data to the report."""
        report_sections = []
        
        try:
            if not hasattr(self, 'gsc_client'):
                return report_sections
            
            site_url = f"https://{self.domain}"
            
            # Get search analytics data
            queries, start_date, end_date = self.gsc_client.get_search_analytics(
                site_url=site_url, days=30)
            
            if not queries:
                return report_sections
            
            # Generate visualizations
            visualizations = self.gsc_client.generate_visualizations(queries)
            
            # Add GSC section to report
            report_sections.append("\n## Google Search Console Performance")
            report_sections.append(f"**Time Period:** {start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}\n")
            
            # Add visualizations
            report_sections.append("### Performance Visualizations")
            report_sections.append("![Device Distribution](gsc_visualizations/device_distribution.png)")
            report_sections.append("![Top Countries](gsc_visualizations/top_countries.png)")
            report_sections.append("![CTR by Position](gsc_visualizations/ctr_by_position.png)\n")
            
            # Top Performing Queries
            report_sections.append("### Top Performing Queries")
            report_sections.append("| Query | Clicks | Impressions | CTR | Position |")
            report_sections.append("|-------|--------|-------------|-----|----------|")
            for query in queries[:5]:  # Show top 5 queries
                report_sections.append(
                    f"| {query['keys'][0]} | {query['clicks']} | {query['impressions']} | "
                    f"{query['ctr']:.2%} | {query['position']:.1f} |"
                )
            
            # Device Performance
            device_data = visualizations['device_distribution']
            report_sections.append("\n### Device Performance")
            report_sections.append("| Device | Clicks | Impressions | CTR |")
            report_sections.append("|--------|--------|-------------|-----|")
            for device, data in device_data.items():
                ctr = data['clicks'] / data['impressions'] if data['impressions'] > 0 else 0
                report_sections.append(
                    f"| {device} | {data['clicks']} | {data['impressions']} | {ctr:.2%} |"
                )
            
            # Geographic Performance
            country_data = visualizations['country_distribution']
            report_sections.append("\n### Geographic Performance")
            report_sections.append("| Country | Clicks | Impressions | CTR |")
            report_sections.append("|---------|--------|-------------|-----|")
            for country, data in sorted(country_data.items(), 
                                      key=lambda x: x[1]['clicks'], 
                                      reverse=True)[:5]:
                ctr = data['clicks'] / data['impressions'] if data['impressions'] > 0 else 0
                report_sections.append(
                    f"| {country} | {data['clicks']} | {data['impressions']} | {ctr:.2%} |"
                )
            
            # Position Analysis
            position_data = visualizations['position_analysis']
            report_sections.append("\n### Position Analysis")
            report_sections.append("| Position Range | Clicks | Impressions | CTR |")
            report_sections.append("|---------------|--------|-------------|-----|")
            for pos in range(1, 11):  # Show top 10 positions
                if pos in position_data:
                    data = position_data[pos]
                    ctr = data['clicks'] / data['impressions'] if data['impressions'] > 0 else 0
                    report_sections.append(
                        f"| {pos} | {data['clicks']} | {data['impressions']} | {ctr:.2%} |"
                    )
            
            # Key Insights
            insights = self.gsc_client.generate_insights(queries, visualizations)
            if insights:
                report_sections.append("\n### Key Insights")
                for i, insight in enumerate(insights, 1):
                    report_sections.append(f"{i}. **{insight['title']}**")
                    for point in insight['points']:
                        report_sections.append(f"   - {point}")
            
            # Recommendations
            recommendations = self.gsc_client.generate_recommendations(queries, visualizations)
            if recommendations:
                report_sections.append("\n### Recommendations")
                for i, rec in enumerate(recommendations, 1):
                    report_sections.append(f"{i}. **{rec['title']}**")
                    for point in rec['points']:
                        report_sections.append(f"   - {point}")
            
            return report_sections
            
        except Exception as e:
            print(f"Error adding GSC data to report: {str(e)}")
            return report_sections

def main():
    parser = argparse.ArgumentParser(description="Generate a detailed site analysis report")
    parser.add_argument("domain", help="Domain name to analyze (e.g., example.com)")
    parser.add_argument("--output", "-o", help="Output file name (default: domain-analysis-report.json)")
    parser.add_argument("--google-doc", "-g", action="store_true", help="Create a Google Doc version of the report")
    parser.add_argument("--share-with", "-s", help="Email address to share the Google Doc with")
    
    args = parser.parse_args()
    
    reporter = SiteReporter(args.domain)
    report = reporter.generate_report()
    reporter.save_report(args.output, args.google_doc, args.share_with)

if __name__ == "__main__":
    main() 