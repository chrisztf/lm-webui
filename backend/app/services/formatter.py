"""
Response formatting service - Provider-grade output structure.
"""
import re
from typing import Optional, Tuple, List

def format_llm_response(
    text: str, 
    context: Optional[dict] = None,
    model_type: str = "generic"
) -> str:
    """
    Format LLM output with smart detection and preservation.
    """
    if not text or not text.strip():
        return text
    
    context = context or {}
    
    # Model-specific preprocessing
    text = _preprocess_by_model(text, model_type)
    
    # Skip formatting for simple responses
    if context.get('preserve_simple') and _is_simple_response(text):
        return text
    
    # Normalize line breaks
    text = text.replace("\r\n", "\n")
    
    # Check if already well-formatted
    if _is_well_formatted(text):
        return text
    
    # Extract and preserve special content
    code_blocks, text = _extract_code_blocks(text)
    citations, text = _extract_citations(text) if context.get('has_citations') else ([], text)
    
    # Format paragraphs - enhanced to handle inline lists
    paragraphs = _split_into_paragraphs(text)
    formatted_paragraphs = []

    for i, paragraph in enumerate(paragraphs):
        if not paragraph.strip():
            formatted_paragraphs.append("")
        else:
            formatted = _process_paragraph(paragraph.strip(), i, len(paragraphs))
            formatted_paragraphs.append(formatted)
    
    formatted_text = '\n\n'.join(formatted_paragraphs)

    # Optional wrap-up (only if requested)
    if context.get('add_wrapup') and len(text) > 200 and not _has_conclusion(text):
        formatted_text = _add_conversational_wrapup(formatted_text)

    return formatted_text


def _is_simple_response(text: str) -> bool:
    """Detect simple Q&A style responses."""
    paragraphs = text.split('\n\n')
    if len(paragraphs) == 1 and len(text) < 150:
        return True
    
    sentences = re.split(r'[.!?]+', text)
    if len(sentences) <= 3 and len(text) < 300:
        return True
    
    return False


def _preprocess_by_model(text: str, model_type: str) -> str:
    """Remove model-specific artifacts."""
    if model_type == "claude":
        text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    elif model_type == "llama":
        text = re.sub(r'<\|.*?\|>', '', text)
    return text


def _extract_code_blocks(text: str) -> Tuple[List[str], str]:
    """Extract code blocks to preserve during formatting."""
    code_blocks = []
    placeholder = "___CODE_BLOCK_{}___|"
    
    def extract(match):
        code_blocks.append(match.group(0))
        return placeholder.format(len(code_blocks) - 1)
    
    text = re.sub(r'```[\s\S]*?```', extract, text)
    return code_blocks, text


def _restore_code_blocks(text: str, code_blocks: List[str]) -> str:
    """Restore preserved code blocks."""
    for i, block in enumerate(code_blocks):
        text = text.replace(f"___CODE_BLOCK_{i}___|", block)
    return text


def _extract_citations(text: str) -> Tuple[List[str], str]:
    """Extract RAG citation markers [1][2]."""
    citations = []
    placeholder = "___CITE_{}___|"
    
    def extract(match):
        citations.append(match.group(0))
        return placeholder.format(len(citations) - 1)
    
    text = re.sub(r'\[(\d+)\]', extract, text)
    return citations, text


def _restore_citations(text: str, citations: List[str]) -> str:
    """Restore citation markers."""
    for i, citation in enumerate(citations):
        text = text.replace(f"___CITE_{i}___|", citation)
    return text


def _contains_table(paragraph: str) -> bool:
    """Strict table detection."""
    lines = paragraph.split('\n')
    
    if len(lines) < 3:
        return False
    
    # Pipe syntax
    pipe_count = sum(1 for l in lines if '|' in l)
    if pipe_count >= 2:
        return True
    
    # Consistent column spacing
    columns = [len(re.split(r'\s{3,}', l)) for l in lines]
    return len(set(columns)) == 1 and columns[0] >= 3


def _split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs, with special handling for inline lists.
    This ensures numbered lists and bullet points get processed as separate paragraphs.
    """
    # First, split by existing paragraph breaks
    paragraphs = text.split('\n\n')

    result_paragraphs = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # Check if this paragraph contains inline numbered lists or bullet points
        if _contains_inline_lists(paragraph):
            # Split the paragraph into sub-paragraphs based on list patterns
            sub_paragraphs = _split_inline_lists(paragraph)
            result_paragraphs.extend(sub_paragraphs)
        else:
            result_paragraphs.append(paragraph)

    return result_paragraphs


def _contains_inline_lists(text: str) -> bool:
    """
    Check if text contains inline numbered lists or bullet points that should be split.
    """
    # Look for patterns like "1. Item 2. Another 3. Third"
    numbered_pattern = r'\d+\.\s+[A-Z][^.!?]*?(?=\s+\d+\.\s+[A-Z]|$)'
    # Look for bullet patterns like "- Item - Another" or "‣ Item ‣ Another"
    bullet_pattern = r'(?:-\s+|‣\s+)[A-Z][^.!?]*?(?=\s+(?:-\s+|‣\s+)[A-Z]|$)'

    numbered_matches = len(re.findall(numbered_pattern, text, re.MULTILINE))
    bullet_matches = len(re.findall(bullet_pattern, text, re.MULTILINE))

    # If we have multiple items of the same type, it's likely a list to split
    return numbered_matches >= 2 or bullet_matches >= 2


def _split_inline_lists(text: str) -> List[str]:
    """
    Split a paragraph containing inline lists into separate paragraphs.
    """
    paragraphs = []

    # Handle numbered lists: "1. First 2. Second 3. Third"
    if re.search(r'\d+\.\s+[A-Z]', text):
        # Split on numbered patterns
        parts = re.split(r'(\d+\.\s+[A-Z][^.!?]*?)(?=\s+\d+\.\s+[A-Z]|$)', text)
        current_para = ""

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if re.match(r'\d+\.\s+[A-Z]', part):
                # This is a list item - start new paragraph if we have content
                if current_para:
                    paragraphs.append(current_para.strip())
                current_para = part
            else:
                current_para += " " + part

        if current_para:
            paragraphs.append(current_para.strip())

    # Handle bullet lists: "- First - Second - Third" or "‣ First ‣ Second ‣ Third"
    elif re.search(r'(?:-\s+|‣\s+)[A-Z]', text):
        # Split on bullet patterns
        parts = re.split(r'((?:-\s+|‣\s+)[A-Z][^.!?]*?)(?=\s+(?:-\s+|‣\s+)[A-Z]|$)', text)
        current_para = ""

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if re.match(r'(?:-\s+|‣\s+)[A-Z]', part):
                # This is a list item - start new paragraph if we have content
                if current_para:
                    paragraphs.append(current_para.strip())
                current_para = part
            else:
                current_para += " " + part

        if current_para:
            paragraphs.append(current_para.strip())

    else:
        # No recognizable list pattern, return as-is
        paragraphs.append(text)

    return paragraphs


def _is_well_formatted(text: str) -> bool:
    """
    Detect if text already contains complex markdown or structured formatting that should be preserved.
    Simple lists (bullets/numbers) are allowed to be enhanced, not preserved.
    """
    import re

    # Complex markdown indicators that should be preserved as-is
    complex_markdown_indicators = [
        r'^#{1,6}\s',                   # Headings (#, ##, ###)
        r'```',                         # Code fences
        r'`[^`]+`',                     # Inline code
        r'\|.*\|',                      # Markdown tables
        r'^-{3,}$',                     # Horizontal rules
        r'\*\*[^*]+\*\*',               # Bold
        r'_[^_]+_',                     # Italic
        r'>\s+',                        # Blockquote
        r'!\[[^\]]*\]\([^)]+\)',        # Image markdown
        r'\[[^\]]+\]\([^)]+\)',         # Links
    ]

    # Early escape: if text is very short, allow processing
    if len(text.strip()) < 40:
        return False

    lines = text.split('\n')
    complex_formatted_lines = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in complex_markdown_indicators:
            if re.search(pattern, stripped):
                complex_formatted_lines += 1
                break

    # Check for complex structures that should be preserved
    has_code_block = "```" in text
    has_table = bool(re.search(r'\|.*\|', text))
    has_heading = bool(re.search(r'^#{1,6}\s', text, flags=re.MULTILINE))

    if has_code_block or has_table or has_heading:
        return True

    # Only consider well-formatted if most lines have complex markdown
    # Exclude simple list patterns from the ratio calculation
    ratio = complex_formatted_lines / max(1, len(lines))
    return ratio >= 0.6  # Higher threshold to allow simple lists to be processed


def _has_conclusion(text: str) -> bool:
    """Check if text already has a conclusion-like ending."""
    conclusion_indicators = [
        r'conclusion\s*:$', r'summary\s*:$', r'recommendation\s*:$',
        r'next steps\s*:$', r'key takeaways\s*:$', r'##?\s+wrap.up',
        r'##?\s+final thoughts', r'##?\s+closing remarks',
        r'thank you', r'let me know', r'feel free', r'questions\?'
    ]
    
    last_paragraph = text.split('\n\n')[-1].lower() if text.split('\n\n') else ""
    
    return any(re.search(pattern, last_paragraph) for pattern in conclusion_indicators)


def _process_paragraph(paragraph: str, index: int, total_paragraphs: int) -> str:
    """Process and format a paragraph intelligently based on its content type."""
    
    paragraph = paragraph.strip()
    if not paragraph:
        return ""  # Skip empty lines
    
    # 1️⃣ Skip if already well-formatted (prevents double formatting)
    if _is_well_formatted(paragraph):
        return paragraph

    # 2️⃣ Detect headings
    if _is_heading_candidate(paragraph, index):
        return _format_heading(paragraph, index)

    # 3️⃣ Detect separators (e.g., "----" or "===")
    if _is_separator(paragraph):
        return "---"

    # 4️⃣ Detect tables early to avoid bullet misclassification
    if _contains_table(paragraph):
        return _format_table(paragraph)

    # 5️⃣ Detect bullet or list content
    if _contains_bullets(paragraph):
        formatted = _format_bullets(paragraph)
        # Recheck formatting consistency
        if not formatted.strip().startswith("-"):
            formatted = "- " + formatted.strip()
        return formatted

    # 6️⃣ Detect actual code blocks (very conservative - only for clear code patterns)
    # Only wrap in code blocks if it looks like actual programming code, not just text with symbols
    code_indicators = [
        r'import\s+\w+',           # Python imports
        r'function\s+\w+\s*\(',    # JavaScript functions
        r'class\s+\w+',            # Class definitions
        r'def\s+\w+\s*\(',         # Python functions
        r'const\s+\w+\s*=',        # JavaScript constants
        r'let\s+\w+\s*=',          # JavaScript variables
        r'var\s+\w+\s*=',          # JavaScript variables
        r'public\s+class',         # Java classes
        r'#include\s*<',           # C/C++ includes
        r'int\s+main\s*\(',        # C/C++ main function
        r'printf\s*\(',            # C printf
        r'console\.log\s*\(',      # JavaScript console.log
        r'print\s*\(',             # Python print
    ]

    is_actual_code = any(re.search(pattern, paragraph, re.IGNORECASE) for pattern in code_indicators)

    # Only wrap as code if it has multiple programming symbols AND looks like code
    # Relaxed threshold: require more symbols to avoid false positives on technical text
    has_many_symbols = len(re.findall(r'[=;{}()<>]', paragraph)) >= 6
    looks_like_code = is_actual_code or (has_many_symbols and len(paragraph.split()) > 10)

    if re.match(r"^\s*```.*", paragraph) or looks_like_code:
        return f"```\n{paragraph}\n```"

    # 7️⃣ Fallback: treat as normal paragraph
    return _format_paragraph(paragraph, index, total_paragraphs)


def _format_paragraph(text: str, index: int, total: int) -> str:
    """Apply soft-wrapping and smooth paragraph flow like ChatGPT."""
    text = re.sub(r'\s{2,}', ' ', text.strip())
    if len(text.split()) < 5 and index < total - 1:
        # Keep short lines merged with the next paragraph naturally
        return text + " "
    return text + "\n"


def _is_heading_candidate(paragraph: str, index: int) -> bool:
    """Determine if paragraph should be formatted as a heading."""
    lines = paragraph.split('\n')
    
    # If it's a single line and looks like a heading
    if len(lines) == 1:
        text = lines[0].strip()
        
        # First paragraph is often an introduction
        if index == 0 and len(text.split()) <= 15:
            return True
        
        # Check for heading patterns
        heading_patterns = [
            r'^\d+\.\s+[A-Z]',  # Numbered headings like "1. Introduction"
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*:',  # Section titles like "Introduction:"
            r'^##?\s+',  # Already has markdown heading
            r'^[A-Z][^.!?]{5,40}$',  # Short, capitalized sentences (no punctuation)
        ]
        
        for pattern in heading_patterns:
            if re.search(pattern, text):
                return True
        
        # Check for question format
        if text.endswith('?') and len(text) < 60:
            return True
    
    return False


def _format_heading(paragraph: str, index: int) -> str:
    """Format paragraph as appropriate heading level."""
    # Remove existing markdown headers if present
    paragraph = re.sub(r'^#+\s+', '', paragraph)
    
    # Use ## for main sections, ### for subsections
    if index == 0:
        # First paragraph gets H2 for introduction
        return f"## {paragraph}"
    else:
        # Subsequent headings get H3
        return f"### {paragraph}"


def _contains_bullets(paragraph: str) -> bool:
    """Detect whether paragraph likely contains bullet-like or list-style content."""
    # Expanded bullet indicators for Markdown, emoji, numeric, and semantic patterns
    bullet_indicators = [
        r'^\s*[-*•‣▪◦●]\s+',            # Common bullet symbols
        r'^\s*\d+[\.\)]\s+',             # Numbered lists like "1." or "2)"
        r'^\s*[a-zA-Z][\.\)]\s+',        # Alphabetical lists like "a)" or "b."
        r'^\s*[-*•‣]\s+[A-Z][a-z]+:',     # Bullet with label like "- Feature:"
        r'^\s*[\u2022-\u2023]\s+',       # Unicode bullet points
        r'^\s*(?:👉|✅|⚡|→|➜|★|☆)\s+',   # Emoji or symbolic bullets
    ]

    # Early check for inline enumeration in a single line (e.g., "1. X 2. Y 3. Z")
    inline_pattern = r'(?:\d+\.\s+[A-Za-z].*?)(?:\s+\d+\.\s+[A-Za-z]){1,}'
    if re.search(inline_pattern, paragraph):
        return True

    # Split by lines to count actual bullets
    lines = paragraph.split('\n')
    bullet_lines = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        for pattern in bullet_indicators:
            if re.search(pattern, stripped):
                bullet_lines += 1
                break

    # Adaptive threshold:
    # - For long paragraphs: require >30% lines to be bullets
    # - For short ones (<4 lines): 1 bullet line is enough
    if len(lines) < 4:
        return bullet_lines >= 1
    else:
        return bullet_lines >= max(1, len(lines) * 0.3)


def _format_bullets(paragraph: str) -> str:
    """Format and enhance bullet styling for better readability."""
    lines = paragraph.split('\n')
    formatted_lines = []

    # If paragraph has no bullets but looks like a list, split into lines
    if len(lines) == 1 and re.search(r'(\d+\.\s|\-\s|•\s)', paragraph) is None:
        # Try to infer list items from punctuation or semicolons
        pseudo_bullets = re.split(r'(?:(?<=:)|;|\.\s+)(?=[A-Z])', paragraph.strip())
        if len(pseudo_bullets) > 1:
            lines = [f"- {item.strip()}" for item in pseudo_bullets if item.strip()]

    for line in lines:
        # Normalize spacing
        line = line.strip()

        # Convert numbered lists or bullets to "- "
        line = re.sub(r'^\s*(?:\d+[\)\.]|[•*])\s+', '- ', line)

        # Enhance bullet formatting with bold keyword → separator
        line = re.sub(r'^-\s+([A-Za-z0-9\s]+?):\s*', r'- **\1** → ', line)
        line = re.sub(r'^-\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*-\s*', r'- **\1** → ', line)

        # Handle common label patterns (pros, cons, steps, tips, etc.)
        common_patterns = [
            (r'^-\s+(Pros?|Cons?|Advantages?|Disadvantages?|Benefits?|Features?|Steps?|Tips?|Causes?|Symptoms?):\s*', r'- **\1** → '),
            (r'^-\s+(Strength|Weakness,Opportunity,Threat):\s*', r'- **\1** → '),
        ]
        for pattern, replacement in common_patterns:
            line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)

        # Ensure spacing between bullets (for Markdown clarity)
        if line.startswith('- ') and not line.endswith('\n'):
            line += '\n'

        formatted_lines.append(line)

    # Join and ensure a blank line between bullet blocks
    formatted_text = '\n'.join(formatted_lines)
    formatted_text = re.sub(r'(\n- )', r'\n\1', formatted_text)  # keep spacing consistent

    return formatted_text.strip()


def _format_table(paragraph: str) -> str:
    """Format paragraph as markdown table."""
    lines = paragraph.split('\n')
    
    # If already has pipe syntax, clean it up
    if any('|' in line for line in lines):
        return _clean_existing_table(lines)
    
    # Otherwise, try to detect column structure
    return _create_table_from_text(lines)


def _clean_existing_table(lines: list) -> str:
    """Clean up existing markdown table syntax."""
    cleaned_lines = []
    
    for i, line in enumerate(lines):
        if '|' in line:
            # Remove extra spaces around pipes
            line = re.sub(r'\s*\|\s*', '|', line)
            line = line.strip('|')
            cleaned_lines.append(f"|{line}|")
        else:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def _create_table_from_text(lines: list) -> str:
    """Create markdown table from text with column-like structure."""
    # Simple implementation: convert to basic table
    # For more sophisticated table detection, this would need NLP
    table_lines = []
    
    # Assume first line is header
    if lines:
        header = lines[0]
        # Try to split by multiple spaces
        columns = re.split(r'\s{2,}', header)
        if len(columns) > 1:
            table_lines.append(f"| {' | '.join(columns)} |")
            table_lines.append(f"|{'---|' * len(columns)}")
            
            # Process data rows
            for line in lines[1:]:
                data_columns = re.split(r'\s{2,}', line, maxsplit=len(columns)-1)
                if len(data_columns) == len(columns):
                    table_lines.append(f"| {' | '.join(data_columns)} |")
    
    return '\n'.join(table_lines) if table_lines else '\n'.join(lines)


def _is_separator(paragraph: str) -> bool:
    """Check if paragraph is a separator."""
    return bool(re.search(r'^-{3,}$', paragraph.strip()))


def _add_conversational_wrapup(text: str) -> str:
    """Add conversational wrap-up to the response."""
    # Don't add if already has a conclusion-like ending
    conclusion_indicators = [
        r'conclusion\s*:$', r'summary\s*:$', r'recommendation\s*:$',
        r'next steps\s*:$', r'key takeaways\s*:$', r'##?\s+wrap.up',
        r'##?\s+final thoughts', r'##?\s+closing remarks'
    ]
    
    last_paragraph = text.split('\n\n')[-1].lower() if text.split('\n\n') else ""
    
    has_conclusion = any(re.search(pattern, last_paragraph) for pattern in conclusion_indicators)
    
    if not has_conclusion:
        # Add a subtle conversational prompt
        wrapup_options = [
            "\n\n---\n*Would you like me to elaborate on any of these points or explore related topics?*",
            "\n\n---\n*Feel free to ask if you'd like more details or have additional questions!*",
            "\n\n---\n*Let me know if you need clarification or want to dive deeper into any aspect.*",
        ]
        
        # Choose based on content length and tone
        if len(text) > 500:
            text += wrapup_options[0]  # More detailed responses get specific offer
        else:
            text += wrapup_options[1]  # Shorter responses get general invitation
    
    return text
