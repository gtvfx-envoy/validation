"""Audit script to check rule context coverage."""

import importlib
import inspect
from pathlib import Path

# Add py directory to path
py_dir = Path(__file__).parent / "py"
import sys
sys.path.insert(0, str(py_dir))

from gt.validator.rules.base import AbstractRule
from gt.runtime import HostType


def audit_rules():
    """Audit all rule classes for context coverage."""
    rules_dir = py_dir / "gt" / "validator" / "rules"
    
    # Import all rule modules
    rule_modules = []
    for py_file in rules_dir.glob("*.py"):
        if py_file.name.startswith("_") or py_file.name == "base.py":
            continue
        
        module_name = f"gt.validator.rules.{py_file.stem}"
        try:
            module = importlib.import_module(module_name)
            rule_modules.append((module.__name__, module))
        except Exception as e:
            print(f"ERROR importing {module_name}: {e}")
    
    # Find all rule classes
    rule_classes = []
    for mod_name, module in rule_modules:
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, AbstractRule) and obj is not AbstractRule:
                rule_classes.append((name, obj, mod_name))
    
    # Audit each rule class
    print(f"Found {len(rule_classes)} rule classes\n")
    print("=" * 80)
    
    issues = []
    for class_name, cls, module_name in sorted(rule_classes):
        context_attr = getattr(cls, 'context', None)
        
        status = "[OK]" if context_attr is not None else "[MISSING]"
        context_str = str(context_attr) if context_attr is not None else "None"
        
        print(f"{status} {class_name:40s} | Context: {context_str}")
        
        # Check for issues
        if context_attr is None:
            issues.append({
                'class': class_name,
                'module': module_name,
                'issue': 'Missing context attribute',
                'severity': 'ERROR'
            })
        elif isinstance(context_attr, HostType):
            # Check if rule is Unreal-only but has STANDALONE context (or vice versa)
            if cls.__name__.startswith(('SkeletalMesh', 'LOD', 'StaticMesh', 'Niagara')):
                if context_attr == HostType.STANDALONE:
                    issues.append({
                        'class': class_name,
                        'module': module_name,
                        'issue': f'Unreal-only rule has STANDALONE context (should be UNREAL)',
                        'severity': 'WARNING'
                    })
    
    print("=" * 80)
    print(f"\nFound {len(issues)} issues:\n")
    
    for issue in sorted(issues, key=lambda x: (-1 if x['severity'] == 'ERROR' else 0, x['class'])):
        print(f"  [{issue['severity']}] {issue['class']:40s} - {issue['issue']}")
        print(f"           Module: {issue['module']}")
    
    return issues


if __name__ == "__main__":
    issues = audit_rules()
    sys.exit(1 if any(i['severity'] == 'ERROR' for i in issues) else 0)
