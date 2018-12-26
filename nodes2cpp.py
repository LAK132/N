bl_info = {"blender": (2, 80, 0), "name": "Nodes2CPP", "category": "Node"}
import bpy
from bpy.props import StringProperty, IntProperty, IntVectorProperty, PointerProperty, FloatProperty, FloatVectorProperty, CollectionProperty, BoolProperty, EnumProperty
from bpy.types import Struct, NodeTree, Node, NodeLinks, NodeSocket, PropertyGroup, Text, Function, ID, Property
from nodeitems_utils import register_node_categories, unregister_node_categories, NodeCategory, NodeItem

def get_input(caller, name, default=None):
    if name not in caller.inputs:
        return default
    sock = caller.inputs[name]
    defval = default
    if sock.is_linked and len(sock.links) > 0 and sock.links[0].is_valid:
        defval = sock.links[0].from_socket.default_value
    else:
        defval = sock.default_value
    return (defval if not hasattr(defval, "value") else defval.value)

def update_chain(socket):
    if socket.is_linked:
        for link in socket.links:
            if link.is_valid:
                link.to_node.update()

def update_value(self, name, value, force=False, none_valid=False):
    if hasattr(self, "outputs"):
        outputs = self.outputs
        if name in outputs.keys():
            if hasattr(outputs[name], "default_value"):
                if hasattr(outputs[name].default_value, "value"):
                    if force or outputs[name].default_value.value != value:
                        outputs[name].default_value.value = value
                elif force or outputs[name].default_value != value:
                    outputs[name].default_value = value
            elif force or outputs[name] != value:
                outputs[name] = value
            update_chain(outputs[name])
        else:
            print("Name '"+name+"' not in outputs")

def find_prop_node(tree, prop):
    if tree is not None and prop is not None:
        for node in tree.nodes:
            for attr in dir(node):
                if getattr(node, attr) == self:
                    return node
    return None

class CallbackOperator(bpy.types.Operator):
    bl_idname = "custom.callback"
    bl_label = "IO Manager"

    options = {}
    identity: StringProperty(name="identity", default="")

    def invoke(self, context, event):
        CallbackOperator.options[self.properties["identity"]]["callback"](
            CallbackOperator.options[self.properties["identity"]]
        )
        return {"FINISHED"}

class UpdateCallbackPropertyGroup(PropertyGroup):
    """Update Callback Property Group"""

    _tree: PointerProperty(name="tree", type=NodeTree)
    _call: StringProperty(name="call", default="update")

    def init(self, tree, call):
        self._tree = tree
        self._call = call

    def update(self, context):
        node = find_prop_node(self._tree, self)
        if hasattr(node, self._call):
            getattr(node, self._call)(context)

class NodeSocketInt3(NodeSocket):
    """Int 3 Socket"""
    bl_idname = "NodeSocketInt3"
    bl_label = "Int 3"
    
    def __getattr__(self, name):
        print("Get attribute "+name+" from "+self)
    
    def update(self, context):
        if not self.is_output:
            self.node.update()
    
    default_value: IntVectorProperty(name="default_value", update=update, size=3)
    
    def draw(self, context, layout, node, label):
        if self.is_output or self.is_linked:
            layout.label(text=label)
        else:
            layout.prop(self, "default_value", text=label)
            
    def draw_color(self, context, node=None):
        return (0.5, 0.0, 1.0, 1.0)

class StringSocket(NodeSocket):
    """String Socket"""
    bl_idname = "StringSocket"
    bl_label = "String"
    
    def __getattr__(self, name):
        print("Get attribute "+name+" from "+self)

    def update(self, context):
        if not self.is_output:
            self.node.update()

    default_value: StringProperty(name="default_value", update=update)

    def draw(self, context, layout, node, label):
        if self.is_output or self.is_linked:
            layout.label(text=label)
        else:
            layout.prop(self, "default_value", text=label)

    def draw_color(self, context, node=None):
        return (0.01, 0.5, 0.08, 1.0)

class StringNode(Node):
    """String Node"""
    bl_idname = "StringNode"
    bl_label = "String"
    bl_icon = "OBJECT_DATA"
    bl_width_min = 230
    
    def __getattr__(self, name):
        print("Get attribute "+name+" from "+self)

    def uda(self, context):
        print("uda")
        self.update()

    def modes(self, context):
        items = [
            ("SUB", "Substring", ""),
            ("CON", "Concatenate", ""),
            ("NEW", "New", "")
        ]
        return items

    def set_sockets(self, sockets):
        for io in ["inputs", "outputs"]:
            selfio = getattr(self, io)
            for sock in selfio:
                if io not in sockets or sock.identifier not in sockets[io]:
                    selfio.remove(sock)
            if io in sockets:
                for name, type in sockets[io].items():
                    if name not in selfio.keys():
                        selfio.new(type, name)

    def change_mode(self, context):
        if self.mode == "NEW":
            self.set_sockets({
                "inputs": {
                    "String": "StringSocket"
                },
                "outputs": {
                    "String": "StringSocket"
                }
            })
        elif self.mode == "CON":
            self.set_sockets({
                "inputs": {
                    "String": "StringSocket",
                    "String 2": "StringSocket"
                },
                "outputs": {
                    "String": "StringSocket"
                }
            })
        elif self.mode == "SUB":
            self.set_sockets({
                "inputs": {
                    "String": "StringSocket",
                    "B:E:S": "NodeSocketInt3"
                },
                "outputs": {
                    "String": "StringSocket"
                }
            })
            self.inputs["B:E:S"].default_value = (0, 10, 1)
        else:
            print("bad mode")

    mode: EnumProperty(name="mode", update=change_mode, items=modes)

    def init(self, context):
        mode = "NEW"
        self.change_mode(context)

    def update(self):
        if self.mode == "NEW":
            str = get_input(self, "String")
            if str is not None:
                print(str)
                update_value(self, "String", str)
        elif self.mode == "CON":
            str1 = get_input(self, "String")
            str2 = get_input(self, "String 2")
            if str1 is not None and str2 is not None:
                print(str1+str2)
                update_value(self, "String", str1+str2)
        elif self.mode == "SUB":
            str = get_input(self, "String")
            sub = get_input(self, "B:E:S")
            if str is not None and sub is not None and len(sub) == 3 and sub[2] is not 0:
                print(str[sub[0]:sub[1]:sub[2]])
                update_value(self, "String", str[sub[0]:sub[1]:sub[2]])

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="Mode")

    def draw_label(self):
        return "String"

class TextFileInputNode(Node):
    """Text File Input Node"""
    bl_idname = "TextFileInputNode"
    bl_label = "Text File Input"
    bl_icon = "OBJECT_DATA"
    bl_width_min = 230
    
    def __getattr__(self, name):
        print("Get attribute "+name+" from "+self)

    def uda(self, context):
        self.update()

    tfile: PointerProperty(type=Text, name="tfile", update=uda)

    def init(self, context):
        self.outputs.new("StringSocket", "Text")

    def update(self):
        if self.tfile is not None:
            update_value(self, "Text", self.tfile.as_string())

    def draw_buttons(self, context, layout):
        layout.template_ID(self, "tfile", new="text.new", unlink="text.unlink", open="text.open")

    def draw_label(self):
        return "Text File Input"

class TextFileOutputNode(Node):
    """Text File Output Node"""
    bl_idname = "TextFileOutputNode"
    bl_label = "Text File Output"
    bl_icon = "OBJECT_DATA"
    bl_width_min = 230
    
    def __getattr__(self, name):
        print("Get attribute "+name+" from "+self)

    def uda(self, context):
        self.update()

    tfile: PointerProperty(type=Text, name="tfile", update=uda)

    def init(self, context):
        self.inputs.new("StringSocket", "Text")

    def update(self):
        text = get_input(self, "Text")
        if self.tfile is not None:
            self.tfile.clear()
            self.tfile.write(text)

    def draw_buttons(self, context, layout):
        layout.template_ID(self, "tfile", new="text.new", unlink="text.unlink", open="text.open")

    def draw_label(self):
        return "Text File Output"

class Nodes2CPPNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return True # context.space_data.tree_type == "Nodes2CPPNodeCategory"

node_categories = [
    Nodes2CPPNodeCategory(
        "FILEIO",
        "File IO",
        items = [
            NodeItem("TextFileInputNode"),
            NodeItem("TextFileOutputNode")
        ]
    ),
    Nodes2CPPNodeCategory(
        "TYPES",
        "Types",
        items = [
            NodeItem("StringNode")
        ]
    )
]

classes = (
    UpdateCallbackPropertyGroup,
    StringSocket,
    NodeSocketInt3,
    TextFileInputNode,
    TextFileOutputNode,
    StringNode
)

register, unregister = bpy.utils.register_classes_factory(classes)

if __name__ == "__main__":
    try:
        unregister_node_categories("NODE2CPP")
        print("unregistered node categories")
    except:
        print("failed to unregister node categories")

    try:
        unregister()
        print("unregistered classes")
    except:
        print("failed to unregister classes")

    try:
        register()
        print("registered classes")
    except:
        print("failed to register classes")

    try:
        register_node_categories("NODES2CPP", node_categories)
        print("registered node categories")
    except:
        print("failed to register node categories")
