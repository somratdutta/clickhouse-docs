#!/usr/bin/env python3

"""
This script can be used to automatically generate a table of contents (JSON file) from the markdown files in a directory,
or multiple directories.
"""

import json
import os
import argparse
import sys
from collections import defaultdict
import yaml
import re

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Script to generate .json table of contents from YAML frontmatter title, description and slug",
    )
    parser.add_argument(
        "--single-toc",
        action="store_true",
        help="Generates a single TOC for all files in all sub-directories of provided directory. By default, generates TOC per folder.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Path to output the resulting table of contents file to (by default it is output to the provided directory - file is named according to --dir)"
    )
    parser.add_argument(
        "--md",
        default=None,
        help="Path to markdown file to append the table of contents to"
    )
    parser.add_argument(
        "--dir",
        help="Path to a folder containing markdown (.md, .mdx) documents containing YAML with title, description, slug."
    )
    parser.add_argument('--ignore', metavar='S', type=str, nargs='+',
                        help='Directory names to ignore. E.g --ignore _snippets images')
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()

def log(message, verbose=False):
    """Print message only if verbose mode is enabled"""
    if verbose:
        print(message)

def extract_title_description_slug(filename, verbose=False):
    data = defaultdict(str)
    missing_fields = []
    frontmatter_data = {}

    try:
        with open(filename, "r") as f:
            content = f.read()
            # find the first frontmatter tag
            frontmatter_start = content.find('---\n')
            if frontmatter_start != -1:
                # find the second frontmatter tag
                frontmatter_end = content.find('---\n', frontmatter_start + 4)
                if frontmatter_start != -1:
                    # find the second frontmatter tag
                    frontmatter_end = content.find('---\n', frontmatter_start + 4)
                    if frontmatter_end != -1:
                        frontmatter_str = content[frontmatter_start+4:frontmatter_end]
                        frontmatter_data = yaml.safe_load(frontmatter_str) or {}

        data.update(frontmatter_data)

        if missing_fields and verbose:
            log(f"Warning: {filename} is missing some fields:", verbose)
            for field in missing_fields:
                log(f"- {field}", verbose)

        return frontmatter_data
    except OSError as e:
        log(f"Ran into a problem reading frontmatter: {e}", verbose)
        sys.exit(1)

def walk_dirs(root_dir, ignore_dirs=[], verbose=False):
    for root, dirs, files in os.walk(root_dir):
        # Modify the 'dirs' list in-place to remove ignored directories
        if (ignore_dirs is not None):
            dirs[:] = [d for d in dirs if d not in ignore_dirs
                       and not any(d.startswith(ig) for ig in ignore_dirs)]
        yield root

def write_md_to_file(json_items, path_to_md_file, verbose=False):
    try:
        # Read existing content
        with open(path_to_md_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()

        # Check if autogenerated tags exist
        start_tag = "<!--AUTOGENERATED_START-->"
        end_tag = "<!--AUTOGENERATED_END-->"

        start_index = existing_content.find(start_tag)
        end_index = existing_content.find(end_tag)

        if start_index == -1 or end_index == -1:
            log(f"Error: Could not find both {start_tag} and {end_tag} tags in {path_to_md_file}", True)  # Always show critical errors
            sys.exit(1)

        if start_index >= end_index:
            log(f"Error: {start_tag} tag appears after {end_tag} tag in {path_to_md_file}", True)  # Always show critical errors
            sys.exit(1)

        # Generate the new table content
        table_content = "\n| Page | Description |\n"
        table_content += "|-----|-----|\n"

        for item in json_items:
            title = item.get('title', '')
            slug = item.get('slug', '')
            description = item.get('description', '')
            link = f"[{title}]({slug})" if slug else title
            table_content += f"| {link} | {description} |\n"

        # Replace content between tags
        before_tags = existing_content[:start_index + len(start_tag)]
        after_tags = existing_content[end_index:]

        new_content = before_tags + table_content + after_tags

        # Write the updated content back to the file
        with open(path_to_md_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

        log(f"Updated markdown table in {path_to_md_file} between autogenerated tags", verbose)

    except Exception as e:
        log(f"An error occurred: {e}", True)  # Always show critical errors
        sys.exit(1)

def write_to_file(json_items, directory, output=None, verbose=False):
    if output is not None:
        # output to the given path the toc.json file
        # If dir='docs/en/interfaces/formats' the file is called docs_en_interfaces_formats_toc.json
        output_path = output+"/"+directory.replace("/", "_")
    else:
        output_path = directory
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)  # Create directories if they don't exist
        with open(output_path, "w") as f:
            json.dump(json_items, f, indent=4, default=str)
            f.write('\n')
            log(f"Wrote {output_path}", verbose)
    except OSError as e:
        if e.errno == 21:
            log(f"Directory already exists: {e}", verbose)
        elif e.errno != 17:
            log(f"An error occurred creating directory: {e}", verbose)

def write_file(json_items, args, directory):
    if (args.out is not None) and (args.md is None):
        write_to_file(json_items, directory+"/toc.json", args.out, args.verbose)
    elif (args.out is None) and (args.md is None):
        write_to_file(json_items, directory+"/toc.json", verbose=args.verbose)
    elif (args.out is None) and (args.md is not None):
        write_md_to_file(json_items, args.md, args.verbose)

def get_title_sort_key(item):
    """Helper function to get the title-based sort key"""
    title = item.get("title", "")
    if "_" in title:
        return title.lower().split("_")[0]  # Sort by part before underscore
    else:
        return title.lower()  # Sort by whole title if no underscore

def sort_by_sidebar_position(json_items, verbose=False):
    if verbose:
        print("Sorting items:")
        for i, item in enumerate(json_items):
            title = item.get("title", "No title")
            sidebar_pos = item.get("sidebar_position", "None")
            print(f"  {i}: {title} (sidebar_position: {sidebar_pos})")

    def sort_key(item):
        # First priority: sidebar_position (if exists and is a number)
        sidebar_position = item.get("sidebar_position")
        if sidebar_position is not None:
            try:
                # Convert to float to handle both int and float values
                key = (0, float(sidebar_position))
                if verbose:
                    print(f"  Using sidebar_position {sidebar_position} for {item.get('title', 'No title')}")
                return key
            except (ValueError, TypeError):
                if verbose:
                    print(f"  Invalid sidebar_position {sidebar_position} for {item.get('title', 'No title')}, falling back to title")
                # If sidebar_position exists but isn't a valid number, fall through to title sorting
                pass

        # Fallback: use the existing title sorting logic
        title_key = get_title_sort_key(item)
        if verbose:
            print(f"  Using title key '{title_key}' for {item.get('title', 'No title')}")
        return (1, title_key)

    sorted_items = sorted(json_items, key=sort_key)

    if verbose:
        print("After sorting:")
        for i, item in enumerate(sorted_items):
            title = item.get("title", "No title")
            sidebar_pos = item.get("sidebar_position", "None")
            print(f"  {i}: {title} (sidebar_position: {sidebar_pos})")

    return sorted_items

def sort_by_title_before_underscore(json_items):
    return sorted(json_items, key=get_title_sort_key)

def main():
    # Extract script arguments
    args = parse_args()
    root_dir = args.dir
    if root_dir is None:
        log("Please provide a directory with argument --dir", True)  # Always show critical errors
        sys.exit(1)
    if os.path.lexists(root_dir) is False:
        log("Path provided does not exist", True)  # Always show critical errors
        sys.exit(1)
    if args.single_toc is True:
        json_items = [] # single list for all directories

    for directory in walk_dirs(root_dir, args.ignore, args.verbose): # Walk directories
        if args.single_toc is False:
            json_items = [] # new list for each directory

        for filename in os.listdir(directory): # for each directory
            full_path = os.path.join(directory, filename)
            if os.path.isfile(full_path) is False:
                continue
            else:
                # index.md is ignored as we expect this to be the page for the table of contents
                if (filename.endswith(".md") or filename.endswith(".mdx")) and filename != "index.md":
                    result = extract_title_description_slug(full_path, args.verbose)
                    if result is not None:
                        json_items.append(result)

        # Sort once after collecting all items for this directory (if not single_toc)
        if args.single_toc is False and len(json_items) > 0:
            json_items = sort_by_sidebar_position(json_items, args.verbose)
            write_file(json_items, args, directory)

    # Sort once after collecting all items from all directories (if single_toc)
    if args.single_toc is True:
        if len(json_items) > 0:
            json_items = sort_by_sidebar_position(json_items, args.verbose)
            write_file(json_items, args, root_dir)  # Use root_dir instead of directory
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
