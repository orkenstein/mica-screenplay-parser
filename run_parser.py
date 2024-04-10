import argparse
from screenplayparser import ScreenplayParser

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Parse a screenplay.')
parser.add_argument('script_path', help='The path to the screenplay to parse.')
args = parser.parse_args()

# instantiate a transformer-based parser by setting use_rules=False
# device_id is the GPU id the parser will use
trx_parser = ScreenplayParser(use_rules=False, device_id=0)

# instantiate a rule-based parser by setting use_rules=True
rule_parser = ScreenplayParser(use_rules=True)

# read a script and save it as a list of strings
# SCRIPT_PATH is the filepath of the movie script
with open(args.script_path) as reader:
    script = reader.read().split("\n")

# trx_tags contains the tag per script line found by the transformer-based parser
# rule_tags contains the tag per script line found by the rule-based parser
trx_tags = trx_parser.parse(script)
rule_tags = rule_parser.parse(script)

print('Transformer-based parser tags:', trx_tags)
print('Rule-based parser tags:', rule_tags)

with open('trx_tags.txt', 'w') as f:
    for tag in trx_tags:
        f.write(f'{tag}\n')

with open('rule_tags.txt', 'w') as f:
    for tag in rule_tags:
        f.write(f'{tag}\n')