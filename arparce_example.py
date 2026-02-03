from model_by_day import calculate_model, run_in_sequence
from datetime import date, timedelta
from time import sleep

import argparse

"""
parser = argparse.ArgumentParser(description="basic parser")
parser.add_argument("--name", action="store_true", help="Name of the user")
#parser.add_argument('-dg',  "--dont_greet", default="User", help="Name of the user")

args = parser.parse_args()

#if not args.dont_greet:
print(f"hello {args.name}")
print(args, type(args))
"""


def absfloat(input):
    return abs(float(input))


parser = argparse.ArgumentParser(description="basic calculator")
subparser = parser.add_subparsers(dest="operations", title="Operations", description="Operations", required=True)

adder = subparser.add_parser("add", help="Adds 1 or more numbers together")
adder.add_argument("--values", help="some numbers", nargs="+", type=absfloat)

multiplier = subparser.add_parser("mult", help="Multiplies 1 or more numbers together")
multiplier.add_argument("--values", help="some numbers", nargs="+", type=float)

args = parser.parse_args()

if args.operations=="add":
    print(f"sum of numbers is {sum(args.values)}")
if args.operations=="mult":
    mult = 1
    for i in args.values:
        mult *= i
    print(f"sum of numbers is {mult}")

print(args, type(args))
