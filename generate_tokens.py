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
from database import init_db, create_tokens


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
        choices=range(5, 13),
        metavar='5-12',
        help='Length of each token (default: 6)'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    # Generate tokens (guaranteed new, never colliding with existing ones)
    print(f"Generating {args.count} tokens...")
    tokens = create_tokens(args.count, args.length)
    print(f"Added {len(tokens)} new tokens to database.")
    
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
