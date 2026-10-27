"""Pure constructors for a method-only image candidate and its held-default proof."""
import ast


def helper(source):
    tree=ast.parse(source)
    cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary')
    node=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='_image')
    assert [n.arg for n in node.args.args]==['self'] and not node.args.defaults
    node.args.args.append(ast.arg(arg='_id'));node.args.defaults.append(ast.Name(id='id',ctx=ast.Load()))
    class Calls(ast.NodeTransformer):
        def visit_Call(self,n):
            if type(n.func) is ast.Name and n.func.id=='id':n.func.id='image_id'
            return self.generic_visit(n)
    Calls().visit(node)
    prefix=ast.parse('''none_ids=[]
def image_id(value):
    if value is None:
        if not none_ids:none_ids.append(_id(value))
        return none_ids[0]
    return _id(value)
''').body
    node.body=prefix+node.body
    lines=source.splitlines(keepends=True)
    return (''.join(lines[:node.lineno-1])+''.join('    '+line+'\n' if line else '\n' for line in ast.unparse(node).splitlines())+''.join(lines[node.end_lineno:])).encode()


def probe(source):
    before="        elif code.co_name=='_audit':expected="
    assert source.count(before)==1
    return source.replace(before,"        elif code.co_name=='_image':expected=(native['id'],)\n"+before,1).encode()
