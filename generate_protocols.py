
import string
import sys
import os


TYPE_NAME = 0
TYPE_RESERVED = 1
TYPE_SYMBOL = 2
TYPE_NUMBER = 3
TYPE_STRING = 4
TYPE_EOF = 5

class Token:
	def __init__(self, type, value, row, col):
		self.type = type
		self.value = value
		self.row = row
		self.col = col
		
		
class FileReader:
	def process(self, filename):
		with open(filename) as f:
			return f.read()
			

NAME_HEAD_CHARS = string.ascii_letters + "_"
NAME_CHARS = NAME_HEAD_CHARS + string.digits

NUMBER_CHARS = string.digits

SPECIAL_CHARS = "{}()[]<>:;,.=!#"

RESERVED_WORDS = ["module", "protocol", "method", "struct", "enum"]
			
CHAR_EOF = "EOF"

class Tokenizer:
	def process(self, data):
		self.tokens = []
		self.state = self.state_next
		
		self.row = 1
		self.col = 1
		for char in data:
			self.state(char)
			
			if char == "\n":
				self.row += 1
				self.col = 1
			else:
				self.col += 1
				
		self.state(CHAR_EOF)
		self.add(TYPE_EOF, None)
		return self.tokens
		
	def error(self, char):
		raise ValueError("Unexpected character at %i:%i in %s: %s" %(self.row, self.col, self.state.__name__, char))
	
	def add(self, type, value):
		token = Token(type, value, self.token_row, self.token_col)
		self.tokens.append(token)
		
	def state_next(self, char):
		self.token_row = self.row
		self.token_col = self.col
		
		if char == '"':
			self.string = ""
			self.state = self.state_string
		elif char in NAME_HEAD_CHARS:
			self.name = char
			self.state = self.state_name
		elif char in NUMBER_CHARS:
			self.number = char
			self.state = self.state_number
		elif char in SPECIAL_CHARS:
			self.add(TYPE_SYMBOL, char)
		elif char in string.whitespace or char == CHAR_EOF:
			pass
		else:
			self.error(char)
			
	def state_name(self, char):
		if char in NAME_CHARS:
			self.name += char
		else:
			if self.name in RESERVED_WORDS:
				self.add(TYPE_RESERVED, self.name)
			else:
				self.add(TYPE_NAME, self.name)
			self.state = self.state_next
			self.state(char)
			
	def state_string(self, char):
		if char == CHAR_EOF:
			self.error(char)
		elif char == '"':
			self.add(TYPE_STRING, self.string)
			self.state = self.state_next
		else:
			self.string += char
			
	def state_number(self, char):
		if char in NUMBER_CHARS:
			self.number += char
		else:
			self.add(TYPE_NUMBER, int(self.number))
			self.state = self.state_next
			self.state(char)

			
class TokenStream:
	def __init__(self, tokens):
		self.tokens = tokens
		self.index = 0
		
	def read(self):
		token = self.tokens[self.index]
		self.index += 1
		return token
	
	def peek(self):
		return self.tokens[self.index]
		
	def rewind(self):
		self.index -= 1
		
	def error(self, token):
		if token.type == TYPE_EOF:
			message = "Unexpected end of file"
		else:
			message = "Unexpected token at %i:%i: %s" %(token.row, token.col, token.value)
		raise ValueError(message)
		
	def read_token(self, type):
		token = self.read()
		if token.type != type:
			self.error(token)
		return token
		
	def parse_token(self, type):
		return self.read_token(type).value
		
	def skip_token(self, type, value):
		token = self.read()
		if token.type != type or token.value != value:
			self.error(token)
			
	def read_name(self): return self.read_token(TYPE_NAME)
	def read_symbol(self): return self.read_token(TYPE_SYMBOL)
		
	def parse_name(self): return self.parse_token(TYPE_NAME)
	def parse_number(self): return self.parse_token(TYPE_NUMBER)
	def parse_string(self): return self.parse_token(TYPE_STRING)
	
	def skip_name(self, value): self.skip_token(TYPE_NAME, value)
	def skip_reserved(self, value): self.skip_token(TYPE_RESERVED, value)
	def skip_symbol(self, value): self.skip_token(TYPE_SYMBOL, value)


class Scope:
	def __init__(self):
		self.names = []
		
	def add(self, name):
		if name in self.names:
			return True
		self.names.append(name)
		return False
		
		
class ModuleSet:
	def __init__(self):
		self.modules = []
		self.scope = Scope()
		
	def add(self, module):
		if self.scope.add(module.name):
			raise ValueError("Module %s already exists" %module.name)
		self.modules.append(module)
		
		
class Module:
	name = None
	
	def __init__(self):
		self.files = []
		
	def add_file(self, file):
		if file in self.files:
			raise ValueError("Duplicate file in module %s: %s" %(self.name, file))
		self.files.append(file)
		
		
class Database:
	def __init__(self):
		self.protocols = []
		self.structs = []
		self.struct_names = []
		self.enums = []
		
		self.scope = Scope()
		
	def add_protocol(self, proto):
		if self.scope.add(proto.name):
			raise ValueError("%s is already defined" %proto.name)
		self.protocols.append(proto)
		
	def add_struct(self, struct):
		if self.scope.add(struct.name):
			raise ValueError("%s is already defined" %struct.name)
		self.structs.append(struct)
		self.struct_names.append(struct.name)
		
	def add_enum(self, enum):
		if self.scope.add(enum.name):
			raise ValueError("%s is already defined" %enum.name)
		self.enums.append(enum)
		
	def update(self, db):
		for proto in db.protocols: self.add_protocol(proto)
		for struct in db.structs: self.add_struct(struct)
		for enum in db.enums: self.add_enum(enum)

	
class Protocol:
	id = None
	name = None
	parent = None
	
	def __init__(self):
		self.methods = []
		self.method_ids = []
		
		self.scope = Scope()
		
	def add_method(self, method):
		if self.scope.add(method.name):
			raise ValueError("%s is already defined in %s" %(method.name, self.name))
		if method.id in self.method_ids:
			raise ValueError("Method id %i is used twice in %s" %(method.id))
		self.methods.append(method)
		self.method_ids.append(method.id)
		

class Method:
	id = None
	name = None
	request = None
	response = None
	supported = None
		
		
class VariableList:
	def __init__(self):
		self.vars = []
		self.scope = Scope()
		
	def add(self, var):
		if self.scope.add(var.name):
			raise ValueError("Duplicate variable name: %s" %var.name)
		self.vars.append(var)
		
		
class Variable:
	type = None
	name = None
	default = None
		
		
class Type:
	name = None
	template = None
		
		
class Struct:
	name = None
	parent = None
	body = None
		
		
class StructBody:
	def __init__(self):
		self.fields = []
		
		self.scope = Scope()
		
	def has_revision(self):
		for field in self.fields:
			if isinstance(field, Revision): return True
			if isinstance(field, Conditional):
				if field.body.has_revision():
					return True
		return False
		
	def add(self, field):
		if isinstance(field, Variable):
			if self.scope.add(field.name):
				raise ValueError("Duplicate variable name in struct: %s" %field.name)
		self.fields.append(field)

		
OPERATOR_EQ = 0
OPERATOR_NE = 1
OPERATOR_LE = 2
OPERATOR_LT = 3
OPERATOR_GE = 4
OPERATOR_GT = 5

OPERATORS = ["==", "!=", "<=", "<", ">=", ">"]

class Conditional:
	group = None
	setting = None
	comparison = None
	value = None
	body = None

		
class Revision:
	revision = None


class Enum:
	name = None
	
	def __init__(self):
		self.values = []
		
		self.scope = Scope()
	
	def add(self, name, value):
		if self.scope.add(name):
			raise ValueError("Name %s used twice in enum %s" %(name, self.name))
		self.values.append((name, value))


TEMPLATE_TYPES = {
	"list": 1,
	"map": 2
}

NUMERIC_TYPES = [
	"uint8", "uint16", "uint32", "uint64",
	"sint8", "sint16", "sint32", "sint64",
	"pid", "datetime"
]

STRING_TYPES = [
	"string", "buffer", "qbuffer"
]


class MetaParser:
	def process(self, tokens):
		stream = TokenStream(tokens)
		return self.parse_file(stream).modules
		
	def parse_file(self, stream):
		set = ModuleSet()
		while True:
			token = stream.peek()
			if token.type == TYPE_EOF:
				return set
			elif token.type == TYPE_RESERVED and token.value == "module":
				set.add(self.parse_module(stream))
			else:
				stream.error(token)
				
	def parse_module(self, stream):
		stream.skip_reserved("module")
		
		module = Module()
		module.name = stream.parse_name()
		stream.skip_symbol("{")
		
		token = stream.peek()
		if token.type == TYPE_SYMBOL and token.value == "}":
			stream.skip_symbol("}")
			return module
		
		while True:
			module.add_file(stream.parse_name())
			
			token = stream.read_symbol()
			if token.value == "}":
				return module
			elif token.value != ",":
				stream.error(token)

		
class ProtoParser:
	def process(self, tokens):
		stream = TokenStream(tokens)
		return self.parse_file(stream)
				
	def parse_file(self, stream):
		db = Database()
		while True:
			token = stream.peek()
			if token.type == TYPE_EOF:
				return db
			elif token.type == TYPE_RESERVED and token.value == "protocol":
				db.add_protocol(self.parse_protocol(stream, db))
			else:
				stream.error(token)
				
	def parse_protocol(self, stream, db):
		stream.skip_reserved("protocol")
		
		protocol = Protocol()
		protocol.name = stream.parse_name()
		stream.skip_symbol(":")
		
		token = stream.read()
		if token.type == TYPE_NUMBER:
			protocol.id = token.value
		elif token.type == TYPE_NAME:
			protocol.parent = token.value
		else:
			stream.error(token)
		stream.skip_symbol("{")
		
		self.prev_method = 0
		
		while True:
			token = stream.peek()
			if token.type == TYPE_SYMBOL and token.value == "}":
				stream.skip_symbol("}")
				return protocol
			elif token.type == TYPE_RESERVED:
				if token.value == "method": protocol.add_method(self.parse_method(stream))
				elif token.value == "struct": db.add_struct(self.parse_struct(stream))
				elif token.value == "enum": db.add_enum(self.parse_enum(stream))
			else:
				stream.error(token)
				
	def parse_method(self, stream):
		stream.skip_reserved("method")
		
		method = Method()
		
		token = stream.peek()
		if token.type == TYPE_SYMBOL and token.value == "(":
			stream.skip_symbol("(")
			method.id = stream.parse_number()
			stream.skip_symbol(")")
		else:
			method.id = self.prev_method + 1
		self.prev_method = method.id
		
		method.name = stream.parse_name()
		
		token = stream.read_symbol()
		if token.value == "(":
			method.request = self.parse_parameter_list(stream)
			stream.skip_symbol("{")
			method.response = self.parse_variable_list(stream)
			method.supported = True
		elif token.value == ";":
			method.supported = False
		else:
			stream.error(token)
		return method
		
	def parse_parameter_list(self, stream):
		list = VariableList()
		
		token = stream.peek()
		if token.type == TYPE_SYMBOL and token.value == ")":
			stream.skip_symbol(")")
			return list
		
		while True:
			list.add(self.parse_variable(stream))
			
			token = stream.read_symbol()
			if token.value == ")":
				return list
			elif token.value != ",":
				stream.error(token)
		
	def parse_variable_list(self, stream):
		list = VariableList()
		
		while True:
			token = stream.peek()
			if token.type == TYPE_SYMBOL and token.value == "}":
				stream.skip_symbol("}")
				return list
			
			list.add(self.parse_variable(stream))
			stream.skip_symbol(";")
	
	def parse_variable(self, stream):
		var = Variable()
		var.type = self.parse_type(stream)
		var.name = stream.parse_name()
		
		token = stream.peek()
		if token.type == TYPE_SYMBOL and token.value == "=":
			stream.skip_symbol("=")
			var.default = self.parse_constant(stream, var.type)
		
		return var
	
	def parse_type(self, stream):
		type = Type()
		type.name = stream.parse_name()
		
		if type.name in TEMPLATE_TYPES:
			type.template = self.parse_template(stream, TEMPLATE_TYPES[type.name])
			
		return type
	
	def parse_template(self, stream, num):
		template = []
		
		stream.skip_symbol("<")
		for i in range(num):
			template.append(self.parse_type(stream))
			if i < num - 1:
				stream.skip_symbol(",")
		stream.skip_symbol(">")
		return template
		
	def parse_constant(self, stream, type):
		if type.name in NUMERIC_TYPES: return stream.parse_number()
		elif type.name in STRING_TYPES: return stream.parse_string()
		elif type.name == "bool":
			token = stream.read_name()
			if token.value not in ["false", "true"]:
				stream.error(token)
			return token.value == "true"
		elif type.name == "list":
			list = []
			
			stream.skip_symbol("[")
			
			token = stream.peek()
			if token.type == TYPE_SYMBOL and token.value == "]":
				stream.skip_symbol("]")
				return list
				
			subtype = type.template[0]
			while True:
				list.append(self.parse_constant(stream, subtype))
				
				token = stream.read_symbol()
				if token.value == "]":
					return list
				elif token.value != ",":
					stream.error(token)
		elif type.name == "map":
			map = {}
			
			stream.skip_symbol("{")
			
			token = stream.peek()
			if token.type == TYPE_SYMBOL and token.value == "}":
				stream.skip_symbol("}")
				return map
				
			keytype = type.template[0]
			valuetype = type.template[1]
			while True:
				key = self.parse_constant(stream, keytype)
				stream.skip_symbol(":")
				value = self.parse_constant(stream, valuetype)
				map[key] = value
				
				token = stream.read_symbol()
				if token.value == "}":
					return map
				elif token.value != ",":
					stream.error(token)
		else:
			raise ValueError("Don't know how to parse constant for %s" %type.name)
			
	def parse_struct(self, stream):
		stream.skip_reserved("struct")
		
		struct = Struct()
		struct.name = stream.parse_name()
		
		token = stream.peek()
		if token.type == TYPE_SYMBOL and token.value == ":":
			stream.skip_symbol(":")
			struct.parent = stream.parse_name()
		
		struct.body = self.parse_struct_body(stream)
		return struct
		
	def parse_struct_body(self, stream):
		body = StructBody()
		
		stream.skip_symbol("{")
		while True:
			token = stream.peek()
			if token.type == TYPE_SYMBOL and token.value == "}":
				stream.skip_symbol("}")
				return body
			
			body.add(self.parse_struct_item(stream))
			
	def parse_struct_item(self, stream):
		token = stream.peek()
		if token.type == TYPE_SYMBOL:
			if token.value == "[": return self.parse_conditional(stream)
			elif token.value == "#": return self.parse_revision(stream)
			else:
				stream.error(token)
		else:
			var = self.parse_variable(stream)
			stream.skip_symbol(";")
			return var
			
	def parse_conditional(self, stream):
		stream.skip_symbol("[")
		
		cond = Conditional()
		cond.group = stream.parse_name()
		stream.skip_symbol(".")
		cond.setting = stream.parse_name()
		cond.operator = self.parse_operator(stream)
		cond.value = stream.parse_number()
		
		stream.skip_symbol("]")
		
		cond.body = self.parse_struct_body(stream)
		return cond
		
	def parse_operator(self, stream):
		token = stream.read_symbol()
		if token.value == ">":
			token = stream.peek()
			if token.type == TYPE_SYMBOL and token.value == "=":
				stream.skip_symbol("=")
				return OPERATOR_GE
			return OPERATOR_GT
		elif token.value == "<":
			token = stream.peek()
			if token.type == TYPE_SYMBOL and token.value == "=":
				stream.skip_symbol("=")
				return OPERATOR_LE
			return OPERATOR_LT
		elif token.value == "!":
			stream.skip_symbol("=")
			return OPERATOR_NE
		elif token.value == "=":
			stream.skip_symbol("=")
			return OPERATOR_EQ
		else:
			return self.error(token)
		
	def parse_revision(self, stream):
		revision = Revision()
		stream.skip_symbol("#")
		stream.skip_name("revision")
		revision.revision = stream.parse_number()
		return revision
		
	def parse_enum(self, stream):
		stream.skip_reserved("enum")
		
		enum = Enum()
		enum.name = stream.parse_name()
		stream.skip_symbol("{")
		
		token = stream.peek()
		if token.type == TYPE_SYMBOL and token.value == "}":
			stream.skip_symbol("}")
			return enum
		
		while True:
			name = stream.parse_name()
			stream.skip_symbol("=")
			value = stream.parse_number()
			enum.add(name, value)
			
			token = stream.read_symbol()
			if token.value == "}":
				return enum
			elif token.value != ",":
				stream.error(token)
				
				
class CodeStream:
	def __init__(self):
		self.code = ""
		self.tabs = 0
		
	def get(self): return self.code
	
	def indent(self): self.tabs += 1
	def unindent(self): self.tabs -= 1
	
	def write(self, text):
		self.code += text
		
	def begin_line(self):
		self.write("\t" * self.tabs)
		
	def write_line(self, line=""):
		self.begin_line()
		self.write(line + "\n")
				
				
BASIC_TYPES = [
	"float", "double", "bool",
	"pid", "result", "datetime",
	"string", "stationurl", "buffer",
	"qbuffer", "anydata"
]

MAPPED_TYPES = {
	"uint8": "u8",
	"uint16": "u16",
	"uint32": "u32",
	"uint64": "u64",
	
	"sint8": "s8",
	"sint16": "s16",
	"sint32": "s32",
	"sint64": "s64",
}
				
class CodeGenerator:
	def process(self, db):
		self.db = db
		
		stream = CodeStream()
		self.generate_file(stream)
		return stream.get()
		
	def generate_file(self, stream):
		self.generate_header(stream)
		for enum in self.db.enums:
			self.generate_enum(stream, enum)
		for struct in self.db.structs:
			self.generate_struct(stream, struct)
		for proto in self.db.protocols:
			self.generate_protocol(stream, proto)
		for proto in self.db.protocols:
			self.generate_client(stream, proto)
		for proto in self.db.protocols:
			self.generate_server(stream, proto)
		
	def generate_header(self, stream):
		stream.write_line()
		stream.write_line("# This file was generated automatically by generate_protocols.py")
		stream.write_line()
		stream.write_line("from nintendo.nex import common")
		stream.write_line()
		stream.write_line("import logging")
		stream.write_line("logger = logging.getLogger(__name__)")
		stream.write_line()
			
	def generate_enum(self, stream, enum):
		stream.write_line()
		stream.write_line("class %s:" %enum.name)
		stream.indent()
		if enum.values:
			for name, value in enum.values:
				stream.write_line("%s = %i" %(name, value))
		else:
			stream.write_line("pass")
		stream.unindent()
		stream.write_line()
		
	def generate_struct(self, stream, struct):
		stream.write_line()
		
		parent = struct.parent
		if parent is None:
			parent = "common.Structure"
		elif parent == "Data":
			parent = "common.Data"
		stream.write_line("class %s(%s):" %(struct.name, parent))
		stream.indent()
		
		self.generate_struct_init(stream, struct)
		self.generate_struct_version(stream, struct)
		self.generate_struct_check(stream, struct)
		self.generate_struct_load(stream, struct)
		self.generate_struct_save(stream, struct)
		
		stream.unindent()
		if struct.parent:
			stream.write_line('common.DataHolder.register(%s, "%s")' %(struct.name, struct.name))
		stream.write_line()
		
	def generate_struct_init(self, stream, struct):
		stream.write_line("def __init__(self):")
		stream.indent()
		stream.write_line("super().__init__()")
		self.generate_struct_init_body(stream, struct.body)
		stream.unindent()
		stream.write_line()
		
	def generate_struct_init_body(self, stream, body):
		for field in body.fields:
			if isinstance(field, Variable):
				stream.write_line("self.%s = %s" %(field.name, self.make_constant(field.type, field.default)))
			elif isinstance(field, Conditional):
				self.generate_struct_init_body(stream, field.body)
			
	def generate_struct_version(self, stream, struct):
		if struct.body.has_revision():
			stream.write_line("def get_version(self, settings):")
			stream.indent()
			stream.write_line("version = 0")
			self.generate_struct_version_body(stream, struct.body)
			stream.write_line("return version")
			stream.unindent()
			stream.write_line()
			
	def generate_struct_version_body(self, stream, body):
		for field in body.fields:
			if isinstance(field, Revision):
				stream.write_line("version = %i" %field.revision)
			elif isinstance(field, Conditional):
				if field.body.has_revision():
					self.generate_if_statement(stream, field)
					stream.indent()
					self.generate_struct_version_body(stream, field.body)
					stream.unindent()
					
	def generate_struct_check(self, stream, struct):
		stream.write_line("def check_required(self, settings):")
		stream.indent()
		self.generate_struct_check_body(stream, struct.body)
		stream.unindent()
		stream.write_line()
		
	def generate_struct_check_body(self, stream, body):
		required = []
		for field in body.fields:
			if isinstance(field, Variable):
				if field.type.name not in self.db.struct_names and \
				   field.type.name != "ResultRange" and \
				   field.default is None:
					required.append(field.name)
		if required:
			stream.write_line("for field in %s:" %required)
			stream.write_line("\tif getattr(self, field) is None:")
			stream.write_line('\t\traise ValueError("No value assigned to required field: %s" %field)')
			
		conditional = [f for f in body.fields if isinstance(f, Conditional)]
		for cond in conditional:
			self.generate_if_statement(stream, cond)
			stream.indent()
			self.generate_struct_check_body(stream, cond.body)
			stream.unindent()
			
		if not required and not conditional:
			stream.write_line("pass")
		
	def generate_struct_load(self, stream, struct):
		stream.write_line("def load(self, stream):")
		stream.indent()
		self.generate_struct_load_body(stream, struct.body)
		stream.unindent()
		stream.write_line()
		
	def generate_struct_load_body(self, stream, body):
		for field in body.fields:
			if isinstance(field, Variable):
				stream.write_line("self.%s = %s" %(field.name, self.make_extract(field.type)))
			elif isinstance(field, Conditional):
				self.generate_if_statement(stream, field, "stream.")
				stream.indent()
				self.generate_struct_load_body(stream, field.body)
				stream.unindent()
		
	def generate_struct_save(self, stream, struct):
		stream.write_line("def save(self, stream):")
		stream.indent()
		stream.write_line("self.check_required(stream.settings)")
		self.generate_struct_save_body(stream, struct.body)
		stream.unindent()
	
	def generate_struct_save_body(self, stream, body):
		for field in body.fields:
			if isinstance(field, Variable):
				stream.write_line(self.make_encode(field.type, "self.%s" %field.name))
			elif isinstance(field, Conditional):
				self.generate_if_statement(stream, field, "stream.")
				stream.indent()
				self.generate_struct_save_body(stream, field.body)
				stream.unindent()
	
	def generate_if_statement(self, stream, cond, prefix=""):
		operator = OPERATORS[cond.operator]
		stream.write_line('if %ssettings.get("%s.%s") %s %i:' %(
			prefix, cond.group, cond.setting, operator, cond.value
		))
		
	def generate_protocol(self, stream, proto):
		name = self.make_class_name(proto.name, "Protocol")
		
		stream.write_line()
		if proto.parent:
			parent = self.make_class_name(proto.parent, "Protocol")
			stream.write_line("class %s(%s):" %(name, parent))
		else:
			stream.write_line("class %s:" %name)
		stream.indent()
		
		for method in proto.methods:
			stream.write_line("METHOD_%s = %i" %(method.name.upper(), method.id))
		if not proto.parent:
			stream.write_line()
			stream.write_line("PROTOCOL_ID = 0x%X" %proto.id)
		
		stream.unindent()
		stream.write_line()
		
	def generate_client(self, stream, proto):
		proto_name = self.make_class_name(proto.name, "Protocol")
		client_name = self.make_class_name(proto.name, "Client")
		
		stream.write_line()
		if proto.parent:
			parent_name = self.make_class_name(proto.parent, "Client")
			stream.write_line("class %s(%s, %s):" %(client_name, parent_name, proto_name))
		else:
			stream.write_line("class %s(%s):" %(client_name, proto_name))
		stream.indent()
		
		if not proto.parent:
			stream.write_line("def __init__(self, client):")
			stream.write_line("\tself.client = client")
			stream.write_line()
			
		first = True
		for method in proto.methods:
			if method.supported:
				if not first:
					stream.write_line()
				else:
					first = False
				self.generate_client_method(stream, proto, method)
		
		stream.unindent()
		stream.write_line()
		
	def generate_client_method(self, stream, proto, method):
		class_name = self.make_class_name(proto.name, "Client")
	
		param = ", ".join(["self"] + [param.name for param in method.request.vars])
		stream.write_line("def %s(%s):" %(method.name, param))
		
		stream.indent()
		stream.write_line('logger.info("%s.%s()")' %(class_name, method.name))
		stream.write_line("#--- request ---")
		stream.write_line("stream, call_id = self.client.init_request(self.PROTOCOL_ID, self.METHOD_%s)" %method.name.upper())
		for param in method.request.vars:
			stream.write_line(self.make_encode(param.type, param.name))
		stream.write_line("self.client.send_message(stream)")
		
		stream.write_line()
		stream.write_line("#--- response ---")
		if len(method.response.vars) > 1:
			stream.write_line("stream = self.client.get_response(call_id)")
			stream.write_line("obj = common.RMCResponse()")
			for var in method.response.vars:
				stream.write_line("obj.%s = %s" %(var.name, self.make_extract(var.type)))
			stream.write_line('logger.info("%s.%s -> done")' %(class_name, method.name))
			stream.write_line("return obj")
		elif len(method.response.vars) == 1:
			value = method.response.vars[0]
			stream.write_line("stream = self.client.get_response(call_id)")
			stream.write_line("%s = %s" %(value.name, self.make_extract(value.type)))
			stream.write_line('logger.info("%s.%s -> done")' %(class_name, method.name))
			stream.write_line("return %s" %value.name)
		else:
			stream.write_line("self.client.get_response(call_id)")
			stream.write_line('logger.info("%s.%s -> done")' %(class_name, method.name))
		stream.unindent()
		
	def generate_server(self, stream, proto):
		server_name = self.make_class_name(proto.name, "Server")
		proto_name = self.make_class_name(proto.name, "Protocol")
	
		stream.write_line()
		if proto.parent:
			parent_name = self.make_class_name(proto.parent, "Server")
			stream.write_line("class %s(%s, %s):" %(server_name, parent_name, proto_name))
		else:
			stream.write_line("class %s(%s):" %(server_name, proto_name))
		stream.indent()
		
		stream.write_line("def __init__(self):")
		stream.indent()
		if not proto.parent:
			stream.write_line("self.methods = {")
			for method in proto.methods:
				stream.write_line("\tself.METHOD_%s: self.handle_%s," %(method.name.upper(), method.name))
			stream.write_line("}")
		else:
			stream.write_line("super().__init__()")
			for method in proto.methods:
				stream.write_line("self.methods[self.METHOD_%s] = self.handle_%s" %(method.name.upper(), method.name))
		stream.unindent()
		
		if not proto.parent:
			stream.write_line()
			stream.write_line("def handle(self, context, method_id, input, output):")
			stream.write_line("\tif method_id in self.methods:")
			stream.write_line("\t\tself.methods[method_id](context, input, output)")
			stream.write_line("\telse:")
			stream.write_line('\t\tlogger.warning("Unknown method called on %s: %i", self.__class__.__name__, method_id)')
			stream.write_line('\t\traise common.RMCError("Core::NotImplemented")')
		
		for method in proto.methods:
			stream.write_line()
			self.generate_server_method(stream, proto, method)
		for method in proto.methods:
			if method.supported:
				stream.write_line()
				self.generate_server_stub(stream, proto, method)
		
		stream.unindent()
		stream.write_line()
		
	def generate_server_method(self, stream, proto, method):
		class_name = self.make_class_name(proto.name, "Server")
	
		stream.write_line("def handle_%s(self, context, input, output):" %method.name)
		
		if not method.supported:
			stream.write_line('\tlogger.warning("%s.%s is unsupported")' %(class_name, method.name))
			stream.write_line('\traise common.RMCError("Core::NotImplemented")')
			return
			
		stream.indent()
		stream.write_line('logger.info("%s.%s()")' %(class_name, method.name))
		stream.write_line("#--- request ---")
		for param in method.request.vars:
			stream.write_line("%s = %s" %(param.name, self.make_extract(param.type, "input")))
		
		params = ", ".join(["context"] + [p.name for p in method.request.vars])
		
		if len(method.response.vars) > 1:
			names = [var.name for var in method.response.vars]
			stream.write_line("response = self.%s(%s)" %(method.name, params))
			stream.write_line()
			stream.write_line("#--- response ---")
			stream.write_line("if not isinstance(response, common.RMCResponse):")
			stream.write_line('\traise RuntimeError("Expected RMCResponse, got %s" %response.__class__.__name__)')
			stream.write_line("for field in %s:" %names)
			stream.write_line("\tif not hasattr(response, field):")
			stream.write_line('\t\traise RuntimeError("Missing field in RMCResponse: %s" %field)')
			for var in method.response.vars:
				stream.write_line(self.make_encode(var.type, "response.%s" %var.name, "output"))
		elif len(method.response.vars) == 1:
			var = method.response.vars[0]
			expected = self.make_python_type(var.type)
			stream.write_line("response = self.%s(%s)" %(method.name, params))
			stream.write_line()
			stream.write_line("#--- response ---")
			stream.write_line("if not isinstance(response, %s):" %expected)
			stream.write_line('\traise RuntimeError("Expected %s, got %%s" %%response.__class__.__name__)' %expected)
			stream.write_line(self.make_encode(var.type, "response", "output"))
		else:
			stream.write_line("self.%s(%s)" %(method.name, params))
		stream.unindent()
		
	def generate_server_stub(self, stream, proto, method):
		class_name = self.make_class_name(proto.name, "Server")
		stream.write_line("def %s(self, *args):" %method.name)
		stream.write_line('\tlogger.warning("%s.%s not implemented")' %(class_name, method.name))
		stream.write_line('\traise common.RMCError("Core::NotImplemented")')
		
	def make_class_name(self, name, type):
		if "_" in name:
			name, ext = name.rsplit("_", 1)
			return "%s%s%s" %(name, type, ext)
		return "%s%s" %(name, type)
		
	def make_python_type(self, type):
		if type.name == "bool": return "bool"
		if type.name == "list": return "list"
		if type.name == "map": return "dict"
		if type.name == "string": return "str"
		if type.name in ["buffer", "qbuffer"]: return "bytes"
		if type.name == "datetime": return "comon.DateTime"
		if type.name == "stationurl": return "common.StationURL"
		if type.name == "result": return "comon.Result"
		if type.name == "anydata": return "common.Data"
		if type.name == "ResultRange": return "common.ResultRange"
		if type.name in self.db.struct_names: return type.name
		if type.name in NUMERIC_TYPES: return "int"
		raise ValueError("Unknown type: %s" %type.name)
				
	def make_constant(self, type, value):
		if type.name in self.db.struct_names: return "%s()" %type.name
		if type.name == "ResultRange": return "common.ResultRange(0, 10)"
		
		if value is None:
			return "None"
		
		if type.name == "datetime": return "common.DateTime(%i)" %value
		if type.name == "string": return '"%s"' %value
		if type.name in ["buffer", "qbuffer"]: return 'b"%s"' %value
		if type.name in NUMERIC_TYPES + ["bool"]: return str(value)
		if type.name == "list":
			entries = []
			for entry in value:
				entries.append(self.make_constant(type.template[0], entry))
			return "[%s]" %", ".join(entries)
		if type.name == "map":
			items = []
			for key, value in value.items():
				key = self.make_constant(type.template[0], key)
				value = self.make_constant(type.template[1], value)
				items.append("%s: %s" %(key, value))
			return "{%s}" %", ".join(items)
		
		raise ValueError("Unknown type: %s" %type.name)		
		
	def make_extract(self, type, stream="stream"):
		if type.name in BASIC_TYPES: return "%s.%s()" %(stream, type.name)
		if type.name in MAPPED_TYPES: return "%s.%s()" %(stream, MAPPED_TYPES[type.name])
		if type.name in self.db.struct_names: return "%s.extract(%s)" %(stream, type.name)
		if type.name == "ResultRange": return "%s.extract(common.ResultRange)" %stream
		if type.name == "list":
			func = self.make_extract_func(type.template[0], stream)
			return "%s.list(%s)" %(stream, func)
		if type.name == "map":
			keyfunc = self.make_extract_func(type.template[0], stream)
			valuefunc = self.make_extract_func(type.template[1], stream)
			return "%s.map(%s, %s)" %(stream, keyfunc, valuefunc)
		raise ValueError("Unknown type: %s" %type.name)
	
	def make_extract_func(self, type, stream="stream"):
		if type.name in BASIC_TYPES: return "%s.%s" %(stream, type.name)
		if type.name in MAPPED_TYPES: return "%s.%s" %(stream, MAPPED_TYPES[type.name])
		if type.name in self.db.struct_names: return type.name
		if type.name == "ResultRange": return "common.ResultRange"
		raise ValueError("Unknown type in list: %s" %type.name)
		
	def make_encode(self, type, name, stream="stream"):
		if type.name == "list":
			func = self.make_encode_func(type.template[0], stream)
			return "%s.list(%s, %s)" %(stream, name, func)
		if type.name == "map":
			keyfunc = self.make_encode_func(type.template[0], stream)
			valuefunc = self.make_encode_func(type.template[1], stream)
			return "%s.map(%s, %s, %s)" %(stream, name, keyfunc, valuefunc)
		return "%s(%s)" %(self.make_encode_func(type, stream), name)
		
	def make_encode_func(self, type, stream="stream"):
		if type.name in BASIC_TYPES: return "%s.%s" %(stream, type.name)
		if type.name in MAPPED_TYPES: return "%s.%s" %(stream, MAPPED_TYPES[type.name])
		if type.name in self.db.struct_names: return "%s.add" %stream
		if type.name == "ResultRange": return "%s.add" %stream
		raise ValueError("Unknown type: %s" %type.name)
		

class Pipeline:
	def __init__(self, *stages):
		self.stages = []
		for stage in stages:
			self.stages.append(stage())
			
	def process(self, param):
		for stage in self.stages:
			param = stage.process(param)
		return param
		

proto_pipeline = Pipeline(FileReader, Tokenizer, ProtoParser)
meta_pipeline = Pipeline(FileReader, Tokenizer, MetaParser)

def process(module):
	db = Database()
	
	for file in module.files:
		filename = "nintendo/files/proto/%s.proto" %file
		
		print("Parsing %s" %filename)
		db.update(proto_pipeline.process(filename))
	
	pyname = "nintendo/nex/%s.py" %module.name
	
	print("Building %s" %pyname)
	code = CodeGenerator().process(db)
	with open(pyname, "wb") as f:
		f.write(code.encode("utf8"))


modules = meta_pipeline.process("nintendo/files/proto/protocols.def")
for module in modules:
	process(module)
