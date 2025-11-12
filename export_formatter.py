#!/usr/bin/env python3
"""
Enhanced Export Formatter for Perplexity AI Wrapper
Provides better formatting for exported content with clear section separation.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class PerplexityExportFormatter:
    """Formats Perplexity responses for better readability in exports"""

    def __init__(self):
        self.section_markers = {
            "related": ["related", "## related", "### related", "related questions"],
            "sources": ["sources", "references", "## sources", "### sources"],
            "follow_up": ["follow-up", "ask a follow-up", "more questions"],
            "share": ["share", "save", "thread actions"],
        }

    def format_response(
        self,
        content: str,
        query: str,
        sources: Optional[List[Dict]] = None,
        related_questions: Optional[List[str]] = None,
        url: Optional[str] = None,
    ) -> str:
        """
        Format a Perplexity response with proper section headers and separation.

        Args:
            content: Raw response content
            query: Original query
            sources: List of source dictionaries
            related_questions: List of related question strings
            url: Source URL

        Returns:
            Formatted markdown content
        """
        if not content:
            return ""

        # Split content into main answer and other sections
        main_answer, extracted_sections = self._split_content_sections(content)

        # Clean and format the main answer
        main_answer = self._clean_main_answer(main_answer, query)

        # Build formatted response
        formatted_parts = []

        # Header
        formatted_parts.append(self._create_header(query, url))

        # Main Answer
        if main_answer:
            formatted_parts.append("## Answer\n")
            formatted_parts.append(main_answer)
            formatted_parts.append("")  # Empty line

        # Sources section
        if sources or extracted_sections.get("sources"):
            formatted_parts.append(
                self._format_sources_section(sources, extracted_sections.get("sources"))
            )
            formatted_parts.append("")

        # Related Questions section
        if related_questions or extracted_sections.get("related"):
            formatted_parts.append(
                self._format_related_section(
                    related_questions, extracted_sections.get("related")
                )
            )
            formatted_parts.append("")

        # Footer
        formatted_parts.append(self._create_footer())

        return "\n".join(formatted_parts)

    def _split_content_sections(self, content: str) -> Tuple[str, Dict[str, str]]:
        """
        Split content into main answer and separate sections.

        Returns:
            Tuple of (main_answer, sections_dict)
        """
        sections = {"sources": "", "related": "", "follow_up": ""}

        lines = content.split("\n")
        main_lines = []
        current_section = "main"
        current_section_lines = []

        for line in lines:
            line_lower = line.strip().lower()

            # Check if this line starts a new section
            section_found = None
            for section_name, markers in self.section_markers.items():
                if any(
                    line_lower.startswith(marker) or line_lower == marker
                    for marker in markers
                ):
                    section_found = section_name
                    break

            if section_found:
                # Save previous section content
                if current_section == "main":
                    main_lines.extend(current_section_lines)
                elif current_section in sections:
                    sections[current_section] = "\n".join(current_section_lines).strip()

                # Start new section
                current_section = section_found
                current_section_lines = []
                # Don't include the section header line in the content
                continue

            current_section_lines.append(line)

        # Save the last section
        if current_section == "main":
            main_lines.extend(current_section_lines)
        elif current_section in sections:
            sections[current_section] = "\n".join(current_section_lines).strip()

        main_answer = "\n".join(main_lines).strip()

        # Clean sections - remove empty ones
        sections = {k: v for k, v in sections.items() if v.strip()}

        return main_answer, sections

    def _clean_main_answer(self, content: str, query: str) -> str:
        """Clean and improve the main answer content."""
        if not content:
            return ""

        lines = content.split("\n")
        cleaned_lines = []

        # Skip query repetition at the start
        if query:
            query_start = query.lower()[:50]
            skip_lines = 0
            for i, line in enumerate(lines[:5]):  # Check first 5 lines
                if query_start in line.lower():
                    skip_lines = i + 1

            lines = lines[skip_lines:]

        # Clean each line
        for line in lines:
            cleaned_line = line.strip()

            # Remove citation markers (like "source+1", "example.com+2")
            cleaned_line = re.sub(r"[a-zA-Z0-9.-]+\+\d+[^\w\s]*", "", cleaned_line)

            # Remove zero-width spaces and other problematic characters
            cleaned_line = (
                cleaned_line.replace("\u200b", "")
                .replace("\u200c", "")
                .replace("\u200d", "")
            )

            # Skip obvious UI elements
            if self._is_ui_element(cleaned_line):
                continue

            if cleaned_line:
                cleaned_lines.append(cleaned_line)

        # Join and clean up excessive whitespace
        result = "\n".join(cleaned_lines)
        result = re.sub(r"\n{3,}", "\n\n", result)

        return result.strip()

    def _is_ui_element(self, line: str) -> bool:
        """Check if a line is likely a UI element that should be filtered out."""
        line_lower = line.lower().strip()

        ui_indicators = [
            "home",
            "discover",
            "library",
            "pro",
            "sign in",
            "sign up",
            "share",
            "save",
            "delete",
            "edit",
            "account",
            "upgrade",
            "thread actions",
            "follow-up",
            "ask a follow-up",
            "more",
            "options",
            "menu",
        ]

        # Single word UI elements
        if line_lower in ui_indicators:
            return True

        # Very short lines that are just UI labels
        if len(line.strip()) < 3:
            return True

        # Lines that are just numbers or single characters
        if re.match(r"^[\d\s\-_]+$", line.strip()):
            return True

        return False

    def _create_header(self, query: str, url: Optional[str] = None) -> str:
        """Create formatted header for the export."""
        header_lines = [
            "# Perplexity Search Results",
            "",
            f"**Query:** {query}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if url:
            header_lines.append(f"**Source:** {url}")

        header_lines.extend(["", "---", ""])

        return "\n".join(header_lines)

    def _format_sources_section(
        self, sources: Optional[List[Dict]], extracted_sources: Optional[str]
    ) -> str:
        """Format sources section with proper headers."""
        lines = ["## Sources"]

        if sources:
            for i, source in enumerate(sources, 1):
                title = source.get("title", "Untitled")
                url = source.get("url", "")
                if url:
                    lines.append(f"{i}. [{title}]({url})")
                else:
                    lines.append(f"{i}. {title}")

        if extracted_sources and not sources:
            # Parse extracted sources text if no structured sources provided
            source_lines = extracted_sources.split("\n")
            for line in source_lines:
                cleaned = line.strip()
                if cleaned and not self._is_ui_element(cleaned):
                    if not cleaned.startswith("*") and not cleaned.startswith("-"):
                        cleaned = f"- {cleaned}"
                    lines.append(cleaned)

        if len(lines) == 1:  # Only header, no sources
            lines.append("*No sources available*")

        return "\n".join(lines)

    def _format_related_section(
        self, related_questions: Optional[List[str]], extracted_related: Optional[str]
    ) -> str:
        """Format related questions section with proper headers."""
        lines = ["## Related Questions"]

        if related_questions:
            for question in related_questions:
                if question.strip():
                    lines.append(f"- {question.strip()}")

        if extracted_related and not related_questions:
            # Parse extracted related questions
            related_lines = extracted_related.split("\n")
            for line in related_lines:
                cleaned = line.strip()
                if cleaned and not self._is_ui_element(cleaned):
                    # Ensure it's formatted as a list item
                    if not cleaned.startswith("*") and not cleaned.startswith("-"):
                        cleaned = f"- {cleaned}"
                    lines.append(cleaned)

        if len(lines) == 1:  # Only header, no questions
            lines.append("*No related questions available*")

        return "\n".join(lines)

    def _create_footer(self) -> str:
        """Create formatted footer for the export."""
        return "\n---\n\n*Exported from Perplexity AI*"

    def format_for_manual_export(self, content: str, query: str, url: str) -> str:
        """
        Format content for manual export when automatic extraction fails.

        Args:
            content: Raw extracted content
            query: Original query
            url: Source URL

        Returns:
            Formatted markdown content
        """
        lines = [
            "# Perplexity Search Results",
            "",
            f"**Query:** {query}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Source:** {url}",
            "",
            "*Note: This is a manual extraction as the automatic export failed.*",
            "",
            "---",
            "",
            "## Content",
            "",
        ]

        if content:
            # Basic cleanup
            cleaned_content = self._clean_main_answer(content, query)
            lines.append(cleaned_content)
        else:
            lines.extend(
                [
                    "*No content could be extracted automatically.*",
                    "",
                    "**Manual Instructions:**",
                    "1. Select all content in your browser (Ctrl+A)",
                    "2. Copy it (Ctrl+C)",
                    "3. Paste it here to replace this text",
                    "4. Save the file",
                ]
            )

        lines.extend(["", "", "---", "", "*Exported from Perplexity AI*"])

        return "\n".join(lines)


def apply_export_formatting(
    content: str,
    query: str,
    sources: List[Dict] = None,
    related_questions: List[str] = None,
    url: str = None,
) -> str:
    """
    Convenience function to apply export formatting.

    Args:
        content: Raw response content
        query: Original search query
        sources: List of source dictionaries
        related_questions: List of related questions
        url: Source URL

    Returns:
        Formatted markdown content
    """
    formatter = PerplexityExportFormatter()
    return formatter.format_response(content, query, sources, related_questions, url)


if __name__ == "__main__":
    # Test the formatter
    test_content = """This is the main answer content about crypto markets.

Bitcoin is currently trading at $35,000.

Related
What is the current price of Ethereum?
How do I buy cryptocurrency?
What are the best crypto wallets?

Sources
coinmarketcap.com
coindesk.com"""

    formatter = PerplexityExportFormatter()
    result = formatter.format_response(
        test_content,
        "What is the current Bitcoin price?",
        url="https://perplexity.ai/search/test",
    )
    print(result)
