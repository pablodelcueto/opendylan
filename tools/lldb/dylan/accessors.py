import lldb

OBJECT_TAG = 0
INTEGER_TAG = 1
BYTE_CHARACTER_TAG = 2
UNICODE_CHARACTER_TAG = 3

GENERIC_FUNCTION_DEBUG_NAME = 3
GENERIC_FUNCTION_METHODS = 4
IMPLEMENTATION_CLASS_REPEATED_SLOT_DESCRIPTOR = 4
IMPLEMENTATION_CLASS_INSTANCE_SLOT_DESCRIPTORS = 17
PAIR_HEAD = 0
PAIR_TAIL = 1
SLOT_DESCRIPTOR_GETTER = 4
SIMPLE_OBJECT_VECTOR_SIZE = 0
SIMPLE_OBJECT_VECTOR_DATA = 1
SYMBOL_NAME = 0

def dylan_tag_bits(value):
  return value.GetValueAsUnsigned() & 3

def dylan_boolean_value(value):
  target = lldb.debugger.GetSelectedTarget()
  true_value = target.FindFirstGlobalVariable('KPtrueVKi').AddressOf().GetValueAsUnsigned()
  return value.GetValueAsUnsigned() == true_value

def dylan_byte_character_value(value):
  byte_value = value.GetValueAsUnsigned() >> 2
  if byte_value < 0 or byte_value > 255:
    return chr(0)
  return chr(byte_value)

def dylan_byte_string_data(value):
  target = lldb.debugger.GetSelectedTarget()
  byte_string_type = target.FindFirstType('dylan_byte_string').GetPointerType()
  value = value.Cast(byte_string_type)
  size = dylan_integer_value(value.GetChildMemberWithName('size'))
  if size == 0:
    return ''
  data = value.GetChildMemberWithName('data').GetPointeeData(0, size + 1)
  error = lldb.SBError()
  string = data.GetString(error, 0)
  if error.Fail():
    return '<error: %s>' % (error.GetCString(),)
  else:
    return string

def dylan_double_integer_value(value):
  target = lldb.debugger.GetSelectedTarget()
  int_type = target.FindFirstType('int')
  lo = dylan_slot_element_raw(value, 0).Cast(int_type)
  hi = dylan_slot_element_raw(value, 1).Cast(int_type)
  return lo.GetValueAsSigned() + (hi.GetValueAsSigned() << 32)

def dylan_generic_function_name(value):
  return dylan_byte_string_data(dylan_slot_element(value, GENERIC_FUNCTION_DEBUG_NAME))

def dylan_generic_function_methods(value):
  return dylan_list_elements(dylan_slot_element(value, GENERIC_FUNCTION_METHODS))

def dylan_implementation_class_instance_slot_descriptors(iclass):
  return dylan_slot_element(iclass, IMPLEMENTATION_CLASS_INSTANCE_SLOT_DESCRIPTORS)

def dylan_implementation_class_repeated_slot_descriptor(iclass):
  return dylan_slot_element(iclass, IMPLEMENTATION_CLASS_REPEATED_SLOT_DESCRIPTOR)

def dylan_integer_value(value):
  return value.GetValueAsUnsigned() >> 2

def dylan_list_elements(value):
  elements = []
  while (dylan_object_class_name(value) != '<empty-list>'):
    elements += [dylan_slot_element(value, PAIR_HEAD)]
    value = dylan_slot_element(value, PAIR_TAIL)
  return elements

def dylan_machine_word_value(value):
  return dylan_slot_element_raw(value, 0).GetValueAsUnsigned()

def dylan_object_class(value):
  iclass = dylan_object_implementation_class(value)
  return iclass.GetChildMemberWithName('the_class')

def dylan_object_class_slot_descriptors(value):
  # XXX: Add the repeated slot descriptor to this.
  iclass = dylan_object_implementation_class(value)
  descriptors = dylan_implementation_class_instance_slot_descriptors(iclass)
  return dylan_vector_elements(descriptors)

def dylan_object_class_slot_names(value):
  return [dylan_slot_descriptor_name(d) for d in dylan_object_class_slot_descriptors(value)]

def dylan_object_class_name(value):
  class_object = dylan_object_class(value)
  return dylan_byte_string_data(class_object.GetChildMemberWithName('debug_name'))

def dylan_object_implementation_class(value):
  value = dylan_value_as_object(value)
  wrapper = value.GetChildMemberWithName('mm_wrapper')
  return wrapper.GetChildMemberWithName('iclass')

def dylan_slot_descriptor_getter(value):
  return dylan_slot_element(value, SLOT_DESCRIPTOR_GETTER)

def dylan_slot_descriptor_name(value):
  getter = dylan_slot_descriptor_getter(value)
  return dylan_generic_function_name(getter)

def dylan_slot_element_raw(value, index):
  dylan_object = dylan_value_as_object(value)
  slots = dylan_object.GetChildMemberWithName('slots')
  return slots.GetChildAtIndex(index, lldb.eNoDynamicValues, True)

def dylan_slot_element(value, index):
  target = lldb.debugger.GetSelectedTarget()
  dylan_value_type = target.FindFirstType('dylan_value')
  slot_value = dylan_slot_element_raw(value, index)
  return slot_value.Cast(dylan_value_type)

def dylan_symbol_name(value):
  name = dylan_slot_element(value, SYMBOL_NAME)
  return dylan_byte_string_data(name)

def dylan_unicode_character_value(value):
  return unichr(value.GetValueAsUnsigned() >> 2).encode('utf8')

def dylan_unicode_string_data(value):
  target = lldb.debugger.GetSelectedTarget()
  byte_string_type = target.FindFirstType('dylan_byte_string').GetPointerType()
  value = value.Cast(byte_string_type)
  size = dylan_integer_value(value.GetChildMemberWithName('size'))
  if size == 0:
    return ''
  # We don't need to read the null termination because we don't want that in
  # our UTF-8 encoded result.
  size = size * 4
  data_pointer = value.GetChildMemberWithName('data').AddressOf().GetValueAsUnsigned(0)
  error = lldb.SBError()
  data = value.process.ReadMemory(data_pointer, size, error)
  if error.Fail():
    return '<error: %s>' % (error.GetCString(),)
  else:
    return data.decode('utf-32').encode('utf-8')

def dylan_value_as_object(value):
  target = lldb.debugger.GetSelectedTarget()
  # We use 'struct _dylan_object' here rather than 'dylan_object' as the latter
  # fails for some reason at the time this was written.
  object_type = target.FindFirstType('struct _dylan_object').GetPointerType()
  return value.Cast(object_type)

def dylan_vector_size(vector):
  return dylan_integer_value(dylan_slot_element(vector, SIMPLE_OBJECT_VECTOR_SIZE))

def dylan_vector_element(vector, index):
  return dylan_slot_element(vector, SIMPLE_OBJECT_VECTOR_DATA + index)

def dylan_vector_elements(vector):
  elements = []
  for idx in range(0, dylan_vector_size(vector)):
    elements += [dylan_vector_element(vector, idx)]
  return elements
