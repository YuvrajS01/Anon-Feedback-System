#!/usr/bin/env python3
"""
Token Generation Script for Anonymous Feedback System.

Usage:
    python generate_tokens.py [count] [--export filename]

Examples:
    python generate_tokens.py 50              # Generate 50 tokens
    python generate_tokens.py 100 --export tokens.txt  # Generate and export to file
"""

import argparse
import random
import string
from database import init_db, add_tokens


def generate_token(length: int = 6) -> str:
    """Generate a random alphanumeric token."""
    # Use uppercase letters and digits for readability
    chars = string.ascii_uppercase + string.digits
    # Exclude similar-looking characters (0, O, I, 1, L)
    chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '').replace('L', '')
    return ''.join(random.choices(chars, k=length))


def generate_unique_tokens(count: int, length: int = 6) -> list:
    """Generate a list of unique tokens."""
    tokens = set()
    while len(tokens) < count:
        tokens.add(generate_token(length))
    return list(tokens)


def main():
    parser = argparse.ArgumentParser(
        description='Generate one-time tokens for the feedback system'
    )
    parser.add_argument(
        'count',
        type=int,
        nargs='?',
        default=10,
        help='Number of tokens to generate (default: 10)'
    )
    parser.add_argument(
        '--export', '-e',
        type=str,
        help='Export tokens to a file'
    )
    parser.add_argument(
        '--length', '-l',
        type=int,
        default=6,
        help='Length of each token (default: 6)'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    # Generate tokens
    print(f"Generating {args.count} tokens...")
    tokens = generate_unique_tokens(args.count, args.length)
    
    # Add to database
    added = add_tokens(tokens)
    print(f"Added {added} new tokens to database.")
    
    # Display tokens
    print("\nGenerated Tokens:")
    print("-" * 40)
    for i, token in enumerate(tokens, 1):
        print(f"{i:4}. {token}")
    
    # Export to file if requested
    if args.export:
        with open(args.export, 'w') as f:
            for token in tokens:
                f.write(token + '\n')
        print(f"\nTokens exported to: {args.export}")
    
    print(f"\nTotal: {len(tokens)} tokens generated")


if __name__ == '__main__':
    main()
