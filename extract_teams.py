import ast

with open(r'c:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv\data\thesportsdb_fixtures.py', 'r', encoding='utf-8') as f:
    content = f.read()

tree = ast.parse(content)

unique_teams = set()

for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id == 'TEAM_ALIASES':
                    if isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(node.value, ast.Dict):
                                # TEAM_ALIASES is {league: {tsdb_name: model_key}}
                                # We need to iterate over the nested dict
                                pass
                if target.id == 'KNOWN_NEW_TO_DIVISION_2627':
                    if isinstance(node.value, ast.Dict):
                        for value in node.value.values:
                            if isinstance(value, (ast.Tuple, ast.List)):
                                for elt in value.elts:
                                    if isinstance(elt, ast.Constant):
                                        unique_teams.add(elt.value)

# Actually, this AST approach is too hard for nested dicts.
# Let's just use a simpler script.

import re

with open(r'c:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv\data\thesportsdb_fixtures.py', 'r', encoding='utf-8') as f:
    text = f.read()

# TEAM_ALIASES: league: {tsdb_name: model_key}
# KNOWN_NEW_TO_DIVISION_2627: league: (team_name, team_name)

# This is tricky because of the structure.
# I'll just print the file content and parse it manually.
print(text)
