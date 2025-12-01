#!/usr/bin/env python3
"""
Network Automation Factory - Main Entry Point

Enterprise AI Agent System for Network Infrastructure Automation
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import OrchestratorAgent, AutomationRequest
from observability.logger import setup_logger
from memory.session_manager import SessionManager

# Setup logging
logger = setup_logger(__name__)


def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        NETWORK AUTOMATION FACTORY                            ║
║        Enterprise AI Agent System                            ║
║                                                              ║
║        Multi-Agent Orchestration for Network DevOps          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Network Automation Factory - AI-powered automation generation"
    )
    
    parser.add_argument(
        "--spec",
        type=str,
        required=True,
        help="Path to automation specification YAML file"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output",
        help="Output directory for generated artifacts (default: ./output)"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        help="Google AI API key (or set GOOGLE_API_KEY env var)"
    )
    
    parser.add_argument(
        "--session-id",
        type=str,
        help="Custom session ID (auto-generated if not provided)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics from memory bank and exit"
    )
    
    return parser.parse_args()


async def main():
    """Main application entry point"""
    
    print_banner()
    
    # Parse arguments
    args = parse_arguments()
    
    # Get API key
    api_key = args.api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key and not args.stats:
        logger.error("Google AI API key required. Set GOOGLE_API_KEY or use --api-key")
        sys.exit(1)
    
    # Show statistics if requested
    if args.stats:
        session_manager = SessionManager()
        stats = session_manager.get_statistics()
        
        print("\n📊 Network Automation Factory Statistics\n")
        print(f"Total Sessions: {stats['total_sessions']}")
        print(f"Average Execution Time: {stats['avg_execution_time']:.2f}s")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Total Agent Calls: {stats['total_agent_calls']}")
        print()
        
        return
    
    # Verify spec file exists
    if not os.path.exists(args.spec):
        logger.error(f"Specification file not found: {args.spec}")
        sys.exit(1)
    
    # Generate session ID
    session_id = args.session_id or f"automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Starting automation request: {session_id}")
    logger.info(f"Specification: {args.spec}")
    logger.info(f"Output directory: {args.output_dir}")
    
    try:
        # Initialize orchestrator
        logger.info("Initializing Network Automation Factory...")
        orchestrator = OrchestratorAgent(
            api_key=api_key,
            output_base_dir=args.output_dir
        )
        
        # Create automation request
        request = AutomationRequest(
            spec_file=args.spec,
            output_dir=args.output_dir,
            session_id=session_id,
            metadata={
                "user": os.getenv("USER", "unknown"),
                "hostname": os.getenv("HOSTNAME", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Process the request
        logger.info("\n🚀 Starting multi-agent workflow...\n")
        result = await orchestrator.process_automation_request(request)
        
        # Display results
        print("\n" + "="*70)
        print("🎉 AUTOMATION FACTORY RESULTS")
        print("="*70)
        
        if result.success:
            print(f"\n✅ Status: SUCCESS")
            print(f"⏱️  Execution Time: {result.execution_time:.2f}s")
            print(f"\n📦 Generated Artifacts ({len(result.artifacts)}):\n")
            
            for artifact_type, path in result.artifacts.items():
                # Make path relative for cleaner display
                rel_path = os.path.relpath(path)
                print(f"   • {artifact_type:20s} → {rel_path}")
            
            if result.metrics:
                print(f"\n📊 Metrics:\n")
                for metric, value in result.metrics.items():
                    print(f"   • {metric:25s}: {value}")
        else:
            print(f"\n❌ Status: FAILED")
            print(f"⏱️  Execution Time: {result.execution_time:.2f}s")
            
            if result.errors:
                print(f"\n🔴 Errors:\n")
                for error in result.errors:
                    print(f"   • {error}")
        
        print("\n" + "="*70)
        
        # Next steps
        if result.success:
            print("\n📋 Next Steps:\n")
            print("   1. Review the generated playbook and documentation")
            print("   2. Check the code review report for any issues")
            print("   3. Run the test suite:")
            print(f"      cd {result.artifacts.get('tests', 'tests/')}")
            print("      molecule test")
            print("   4. Deploy using the CI/CD pipeline configuration")
            print()
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Operation cancelled by user")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {str(e)}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(130)
