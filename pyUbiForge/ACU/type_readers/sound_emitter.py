from pyUbiForge.misc.file_object import FileObjectDataWrapper
from pyUbiForge.misc.file_readers import BaseReader


class Reader(BaseReader):
	file_type = '0423BD15'

	def __init__(self, py_ubi_forge, file_object_data_wrapper: FileObjectDataWrapper):
		file_object_data_wrapper.read_bytes(24)
