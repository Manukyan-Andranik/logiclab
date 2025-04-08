# from bs4 import BeautifulSoup
# import tinycss2
# import re
# import os

# def extract_html_selectors(html_path):
#     """Extract all selectors (tags, classes, ids) from HTML file"""
#     with open(html_path, 'r', encoding='utf-8') as f:
#         soup = BeautifulSoup(f, 'html.parser')
    
#     # Get all used tags, classes, and ids
#     tags = {tag.name for tag in soup.find_all()}
#     classes = {cls for tag in soup.find_all(class_=True) 
#                for cls in tag.get('class', [])}
#     ids = {tag.get('id') for tag in soup.find_all(id=True) if tag.get('id')}
    
#     # Also extract selectors from inline styles
#     inline_styles = [tag['style'] for tag in soup.find_all(style=True)]
#     for style in inline_styles:
#         # Extract class-like and id-like references
#         classes.update(re.findall(r'\.([\w-]+)', style))
#         ids.update(re.findall(r'#([\w-]+)', style))
    
#     return tags, classes, ids

# def is_selector_used(selector, tags, classes, ids):
#     """Check if a CSS selector is used in the HTML"""
#     # Check for :root selector (CSS variables)
#     if selector == ':root':
#         return True
    
#     # Check for simple element selectors (div, p, etc.)
#     if re.match(r'^\w+$', selector):
#         return selector in tags
    
#     # Check for class selectors (.my-class)
#     class_matches = re.findall(r'\.([\w-]+)', selector)
#     if class_matches and any(cls in classes for cls in class_matches):
#         return True
    
#     # Check for ID selectors (#my-id)
#     id_matches = re.findall(r'#([\w-]+)', selector)
#     if id_matches and any(id_ in ids for id_ in id_matches):
#         return True
    
#     # Consider pseudo-classes (:hover) and attribute selectors ([type="text"]) as potentially used
#     if ':' in selector or '[' in selector:
#         return True
    
#     # Consider keyframes (@keyframes) as used
#     if selector.startswith('@keyframes'):
#         return True
    
#     # Consider media queries as used
#     if selector.startswith('@media'):
#         return True
    
#     return False

# def filter_css_rules(css_path, html_selectors):
#     """Filter CSS rules to only those used in the HTML"""
#     tags, classes, ids = html_selectors
    
#     with open(css_path, 'r', encoding='utf-8') as f:
#         css_content = f.read()
#     print(css_content)
#     # Parse CSS while preserving rules structure
#     rules = tinycss2.parse_stylesheet(css_content, skip_comments=True, skip_whitespace=True)
#     used_rules = []
    
#     for rule in rules:
#         if rule.type == 'qualified-rule':
#             prelude = tinycss2.serialize(rule.prelude).strip()
#             selectors = [s.strip() for s in prelude.split(',') if s.strip()]
            
#             # Check if any selector in this rule matches HTML elements
#             if any(is_selector_used(selector, tags, classes, ids) for selector in selectors):
#                 used_rules.append(rule)
#         elif rule.type == 'at-rule':
#             # Handle @keyframes and @media rules more safely
#             try:
#                 if hasattr(rule, 'name') and rule.name in ('keyframes', 'media'):
#                     used_rules.append(rule)
#             except AttributeError:
#                 # Log and skip any invalid at-rule that does not have a 'name'
#                 print(f"Error processing at-rule: {rule}, missing 'name' attribute")
#     return used_rules

# def write_optimized_css(rules, output_path):
#     """Write the filtered CSS rules to a new file with proper formatting"""
#     with open(output_path, 'w', encoding='utf-8') as f:
#         for rule in rules:
#             if rule.type == 'qualified-rule':
#                 selector = tinycss2.serialize(rule.prelude).strip()
#                 declarations = []
                
#                 for node in rule.content:
#                     if node.type == 'declaration':
#                         declarations.append(tinycss2.serialize([node]).strip())
                
#                 if declarations:
#                     f.write(selector + " {\n  " + ";\n  ".join(declarations) + ";\n}\n\n")

#                     # f.write(f"{selector} {{\n  {';\n  '.join(declarations)};\n}}\n\n")
            
#             elif rule.type == 'at-rule':
#                 if rule.name == 'keyframes':
#                     name = tinycss2.serialize(rule.prelude).strip()
#                     content = tinycss2.serialize(rule.content)
#                     print(name, content)
#                     f.write(f"@keyframes {name} {{\n{content}\n}}\n\n")
#                 elif rule.name == 'media':
#                     media_query = tinycss2.serialize(rule.prelude).strip()
#                     content = tinycss2.serialize(rule.content)
#                     print(media_query, content)
                    
#                     f.write(f"@media {media_query} {{\n{content}\n}}\n\n")

# def create_index_css(html_path, css_path, output_path):
#     """Main function to create index-specific CSS file"""
#     print(f"Processing {html_path} and {css_path}...")
    
#     # Extract selectors from HTML
#     html_selectors = extract_html_selectors(html_path)
#     print(f"Found {len(html_selectors[0])} tags, {len(html_selectors[1])} classes, {len(html_selectors[2])} IDs in HTML")
    
#     # Filter CSS rules
#     used_rules = filter_css_rules(css_path, html_selectors)
#     print(f"Found {len(used_rules)} used CSS rules")
    
#     # Write output file
#     write_optimized_css(used_rules, output_path)
#     print(f"Created optimized CSS file at {output_path}")
    
#     # Calculate reduction
#     original_size = os.path.getsize(css_path)
#     new_size = os.path.getsize(output_path)
#     reduction = (1 - new_size/original_size) * 100
#     print(f"Reduced CSS size by {reduction:.1f}% (from {original_size} to {new_size} bytes)")

# if __name__ == '__main__':
#     # Configure paths
#     HTML_FILE = 'templates/index.html'
#     CSS_FILE = 'static/css/style.css'
#     OUTPUT_FILE = 'static/css/index_style.css'
    
#     # Run the processor
#     create_index_css(HTML_FILE, CSS_FILE, OUTPUT_FILE)

import re

def func(css_path=None, html_path=None):
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()
    print(type(css_content))
    # Match selectors followed by an opening curly brace
    matches = re.findall(r'([^{]+)\s*\{', css_content)

    for wl in matches:
        with open("static/css/index_style.css", 'w', encoding='utf-8') as f:
            f.write(wl)
    #     for match in matches:
    #         match = match.strip()
    #         if match.startswith('.'):
    #             # Class selector
    #             class_name = match[1:]
    #             if f'class="{class_name}"' in html_content:
    #                 f.write(f'{match} {{\n')
    #                 f.write('  /* CSS rules here */\n')
    #                 f.write('}\n\n')
    #         elif match.startswith('#'):
    #             # ID selector
    #             id_name = match[1:]
    #             if f'id="{id_name}"' in html_content:
    #                 f.write(f'{match} {{\n')
    #                 f.write('  /* CSS rules here */\n')
    #                 f.write('}\n\n')
    #         else:
    #             # Tag selector
    #             tag_name = match
    #             if f'<{tag_name}' in html_content:
    #                 f.write(f'{match} {{\n')
    #                 f.write('  /* CSS rules here */\n')
    #                 f.write('}\n\n')
func(css_path='static/css/style.css', html_path='templates/index.html')