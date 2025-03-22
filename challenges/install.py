#!/usr/bin/env python3
"""
CTF Challenge Deployment Script

This script handles deployment of CTF (Capture The Flag) exercises to LXD VMs.
It supports template processing, random IP assignment, flag generation, and
manages Docker containers for each exercise.
"""

import argparse
from utils import CTFDeployer


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Deploy CTF exercises to LXD VMs')
    parser.add_argument('--config', default='config.yaml', help='Path to configuration file')
    parser.add_argument('--category', required=True, help='Category name for exercises (e.g., access_control, docker_escape)')
    parser.add_argument('--force', action='store_true', help='Force overwrite of existing files')
    args = parser.parse_args()
    
    # Create deployer and run deployment
    deployer = CTFDeployer(args.config, args.category, args.force)
    deployer.deploy()

if __name__ == '__main__':
    main()