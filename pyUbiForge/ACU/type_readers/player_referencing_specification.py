from pyUbiForge.misc.file_object import FileObjectDataWrapper
from pyUbiForge.misc.file_readers import BaseReader


class Reader(BaseReader):
	file_type = '9E1CD34A'

	def __init__(self, py_ubi_forge, file_object_data_wrapper: FileObjectDataWrapper):
		count = file_object_data_wrapper.read_uint_32()
		# for _ in range(count):  # the above looks like a count but there is only 1 of the below
		py_ubi_forge.read_file.get_data_recursive(file_object_data_wrapper)
