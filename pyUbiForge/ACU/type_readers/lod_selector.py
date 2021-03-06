from pyUbiForge.misc.file_object import FileObjectDataWrapper
from pyUbiForge.misc.file_readers import BaseReader


class Reader(BaseReader):
	file_type = '01437462'

	def __init__(self, py_ubi_forge, file_object_data_wrapper: FileObjectDataWrapper):
		file_object_data_wrapper.read_bytes(1)
		file_object_data_wrapper.read_id()
		file_object_data_wrapper.out_file_write('\n')
		self.lod = []
		for _ in range(5):
			ending0 = file_object_data_wrapper.read_uint_8()
			if ending0 == 0:
				self.lod.append(py_ubi_forge.read_file.get_data_recursive(file_object_data_wrapper))
			elif ending0 == 3:
				self.lod.append(None)
			else:
				raise Exception()
