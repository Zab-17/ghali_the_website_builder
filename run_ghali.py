#!/usr/bin/env python3 -u
"""
Call Ghali from your terminal:

  python run_ghali.py                              # Build site for next lead from sheet
  python run_ghali.py 3                            # Build sites for next 3 leads
  python run_ghali.py "Restaurant Name"            # Build site for specific business
  python run_ghali.py 20 --instance A              # Build 20 leads as instance "A" (dashboard tracking)
"""

import sys
import asyncio

from agent.orchestrator import run_ghali


def main():
    target = None
    count = 1
    instance = None

    # Parse --instance flag
    args = sys.argv[1:]
    if "--instance" in args:
        idx = args.index("--instance")
        if idx + 1 < len(args):
            instance = args[idx + 1]
            args = args[:idx] + args[idx + 2:]

    if args:
        arg = args[0]
        if arg.isdigit():
            count = int(arg)
            label = f" [{instance}]" if instance else ""
            print(f"Waking up Ghali{label} to build sites for {count} leads...")
        else:
            target = arg
            print(f'Waking up Ghali to build a site for: "{target}"')
    else:
        print("Waking up Ghali... Building site for next lead.")

    asyncio.run(run_ghali(target=target, count=count))


if __name__ == "__main__":
    main()
