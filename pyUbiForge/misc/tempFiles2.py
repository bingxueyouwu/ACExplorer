import os
import json
import numpy
from typing import Union, Tuple, Dict
from pyUbiForge.misc.file_object import FileObjectDataWrapper

"""
Forge file
Forge1.forge
	dataFile1
		file1
		file2
		...
	dataFile2
		file1
		file2
		...
	dataFile3
		file1
		file2
		...
	...
Forge2.forge
	dataFile1
		file1
		file2
		...
	dataFile2
		file1
		file2
		...
	dataFile3
		file1
		file2
		...
	...
"""

"""
tempFiles
{
	<fileID>:(<forgeFile>, <datafileID>, <fileType>, <fileName>, None),
	...
}
"""

"""
lightDictionary
{
	fileID:{
		<forgeFile>:[]
	}
}
"""


class TempFile:
	def __init__(self, py_ubi_forge, forge_file: str, datafile_id: int, file_id: int, file_type: str, file_name: str, raw_file: bytes):
		"""Container for data related to a file.
		Should help with typing and argument selection compared to the old dictionary method
		"""
		self._pyUbiForge = py_ubi_forge
		self._forge_file = forge_file
		self._datafile_id = datafile_id
		self._file_id = file_id
		self._file_type = file_type
		self._file_name = file_name
		self._raw_file = raw_file

	@property
	def forge_file(self) -> str:
		"""The name of the forge file the file is contained in."""
		return self._forge_file

	@property
	def datafile_id(self) -> int:
		"""The numerical id of the datafile the file is contained in.
		In some cases this may be the same as the file_id since every datafile will have containing file with the same id.
		"""
		return self._datafile_id

	@property
	def file_id(self) -> int:
		"""The numerical file id relating to the file.
		Theoretically this is unique to that file but there are some duplicates.
		From what I can tell all files with the same id contain the same data.
		"""
		return self._file_id

	@property
	def file_type(self) -> str:
		"""The big endian hexadecimal representation of the file type."""
		return self._file_type

	@property
	def file_name(self) -> str:
		"""The name of the file"""
		return self._file_name

	@property
	def file(self) -> FileObjectDataWrapper:
		"""The raw data wrapped up in a custom data wrapper.
		See FileObjectDataWrapper for more information.
		"""
		return FileObjectDataWrapper.from_binary(self._pyUbiForge, self._raw_file)


class LastUsed:
	def __init__(self):
		self._position_to_data = {}
		self._data_to_position = {}
		self._min = 0
		self._max = 0

	def remove(self, data: int):
		if data in self._data_to_position:
			position = self._data_to_position[data]
			del self._data_to_position[data]
			del self._position_to_data[position]

	def pop(self):
		while self._min not in self._position_to_data and self._min < self._max:
			self._min += 1
		if self._min == self._max:
			return
		else:
			data = self._position_to_data[self._min]
			del self._position_to_data[self._min]
			del self._data_to_position[data]
			return data

	def append(self, data: int):
		self._position_to_data[self._max] = data
		self._data_to_position[data] = self._max
		self._max += 1

	def clear(self):
		self._position_to_data.clear()
		self._data_to_position.clear()
		self._min = 0
		self._max = 0


class LightDictionary:
	def __init__(self, py_ubi_forge):
		self.pyUbiForge = py_ubi_forge
		self._light_dictionary_numpy = numpy.empty(0, dtype=[('file_id', numpy.uint64), ('forge_file', numpy.uint8), ('datafile_id', numpy.uint64)])
		self._light_dictionary_temp = []
		self._light_dictionary: Dict[Tuple[int, int], int] = {}
		self._light_dictionary_no_forge: Dict[int, Tuple[int, int]] = {}
		self._changed = False
		self._forge_to_index = {}
		self._index_to_forge = {}
		self._max_forge_index = 0

	def clear(self):
		self._light_dictionary_numpy = numpy.empty(0, dtype=[('file_id', numpy.uint64), ('forge_file', numpy.uint8), ('datafile_id', numpy.uint64)])
		self._light_dictionary_temp = []
		self._light_dictionary.clear()
		self._light_dictionary_no_forge.clear()
		self._changed = False
		self._forge_to_index.clear()
		self._index_to_forge.clear()
		self._max_forge_index = 0

	def _forge_index(self, forge_file_name: str) -> int:
		if forge_file_name not in self._forge_to_index:
			self._forge_to_index[forge_file_name] = self._max_forge_index
			self._index_to_forge[self._max_forge_index] = forge_file_name
			self._max_forge_index += 1
		return self._forge_to_index[forge_file_name]

	@property
	def changed(self):
		return self._changed

	@property
	def list(self) -> list:
		return list(self._light_dictionary_no_forge.items())

	def load(self):
		"""Load the light dictionary file from disk into memory if it exists."""
		self.clear()

		if os.path.isfile(f'./resources/lightDict/{self.pyUbiForge.game_functions.game_identifier}.ld'):
			with open(f'./resources/lightDict/{self.pyUbiForge.game_functions.game_identifier}.ld', 'rb') as light_dict:
				header_len = int(numpy.fromfile(light_dict, numpy.uint32, 1))
				header = json.loads(light_dict.read(header_len).decode('utf-8'))
				self._forge_to_index = header['forge_index']
				self._light_dictionary_numpy = numpy.fromfile(
					light_dict,
					numpy.uint64
					# [
					# 	('file_id', numpy.uint64),
					# 	('forge_file', numpy.uint64),
					# 	('datafile_id', numpy.uint64)
					# ]
				).reshape((-1, 3))
				self._light_dictionary = dict(
					zip(
						map(
							tuple,
							self._light_dictionary_numpy[:, :2]
						),
						self._light_dictionary_numpy[:, 2]
					)
				)
				self._light_dictionary_no_forge = dict(
					zip(
						self._light_dictionary_numpy[:, 0],
						map(
							tuple,
							self._light_dictionary_numpy[:, 1:]
						)
					)
				)
			self._max_forge_index = len(self._forge_to_index)
			self._index_to_forge = {val: key for key, val in self._forge_to_index.items()}

	def save(self):
		"""Save the light dictionary in memory back to disk if it has changed."""
		self._merge_light_dict_temp()
		if self.changed:
			if not os.path.isdir('./resources/lightDict'):
				os.makedirs('./resources/lightDict')
			header = json.dumps(
				{
					'forge_index': self._forge_to_index
				}
			).encode()
			with open(f'./resources/lightDict/{self.pyUbiForge.game_functions.game_identifier}.ld', 'wb') as f:
				numpy.uint32(len(header)).tofile(f)
				f.write(header)
				_, index = numpy.unique(self._light_dictionary_numpy[:, :2], axis=0, return_index=True)
				self._light_dictionary_numpy[index, :].tofile(f)

	def get(self, file_id: int, forge_file_name: str = None) -> Union[Tuple[str, int], Tuple[None, None]]:
		"""Find a datafile containing a file id with optional forge file name

		:param file_id: numerical file id of an end file
		:param forge_file_name: string name of the forge file (optional)
		:return: (forge file name, datafile id)
		"""
		if forge_file_name is not None:
			forge_file_index = self._forge_index(forge_file_name)
			if (file_id, forge_file_index) in self._light_dictionary:
				return forge_file_name, self._light_dictionary[(file_id, forge_file_index)]
		if file_id in self._light_dictionary_no_forge:
			forge_file_index, datafile_id = self._light_dictionary_no_forge[file_id]
			return self._index_to_forge[forge_file_index], datafile_id
		else:
			return None, None

	def add(self, file_id: int, forge_file_name: str, datafile_id: int):
		forge_file_index = self._forge_index(forge_file_name)
		if (file_id, forge_file_index) not in self._light_dictionary:
			self._light_dictionary[(file_id, forge_file_index)] = datafile_id
			if file_id not in self._light_dictionary_no_forge:
				self._light_dictionary_no_forge[file_id] = (forge_file_index, datafile_id)
			self._light_dictionary_temp.append(
				(file_id, forge_file_index, datafile_id)
			)

	def _merge_light_dict_temp(self):
		if len(self._light_dictionary_temp) > 0:
			self._light_dictionary_numpy = numpy.append(
				self._light_dictionary_numpy,
				numpy.array(self._light_dictionary_temp, numpy.uint64),
				axis=0
			)
			self._light_dictionary_temp = []
			self._changed = True


class TempFilesContainer:
	"""Class to hold all the files and the methods to access them and pull them from the original files."""
	def __init__(self, py_ubi_forge):
		self.pyUbiForge = py_ubi_forge
		# dictionary to look up which dataFile a fileID is contained in (if it itself is not the main file in the dataFile)
		self.light_dictionary = LightDictionary(py_ubi_forge)
		# the amount of memory self.rawFiles takes (used to remove files)
		self._memory = 0
		# a dictionary of every file currently loaded into memory
		self._temp_files = {}
		self._last_used = LastUsed()

	@property
	def light_dict_changed(self) -> bool:
		return self.light_dictionary.changed

	@property
	def list_light_dictionary(self) -> list:
		return self.light_dictionary.list

	def add(self, file_id: int, forge_file_name: str, datafile_id: int, file_type: int, file_name: str, raw_file: bytes = None):
		"""
		:param file_id: int
		:param forge_file_name: str
		:param datafile_id: int of containing datafile
		:param file_type: int
		:param file_name: str
		:param raw_file: binary
		"""
		if file_id in self._temp_files:
			self._memory -= len(self._temp_files[file_id][4])
		self.refresh_usage(file_id)
		self._temp_files[file_id] = (forge_file_name, datafile_id, file_type, file_name, raw_file)
		if raw_file is not None:
			self._memory += len(raw_file)

		while self._memory > self.pyUbiForge.CONFIG.get('tempFilesMaxMemoryMB', 2048)*1000000:
			remove_entry = self._last_used.pop()
			self._memory -= len(self._temp_files[remove_entry][4])
			del self._temp_files[remove_entry]

		if file_id != datafile_id:
			self.light_dictionary.add(file_id, forge_file_name, datafile_id)

	def __call__(self, file_id: int, forge_file_name: str = None, datafile_id: int = None) -> Union[None, TempFile]:
		"""Tries to find the file matching the description and return a TempFile class containing the data.
		Returns None if it cannot find the file.
		:param file_id: int
		:param forge_file_name: str
		:param datafile_id: int of the containing datafile
		:return: TempFile, None
		"""
		if not isinstance(file_id, int):
			if isinstance(file_id, numpy.integer):
				file_id = int(file_id)
			else:
				raise Exception(f'Expected an integer type but got {type(file_id)}')
		if file_id == 0:
			return

		if forge_file_name is not None and datafile_id is None:
			if file_id in self._temp_files and forge_file_name == self._temp_files[file_id][0]:
				datafile_id = self._temp_files[file_id][1]
			else:
				# preferentially use one found in the forgeFile asked but look in others if needed
				if forge_file_name in self.pyUbiForge.forge_files and file_id in self.pyUbiForge.forge_files[forge_file_name].datafiles:
					datafile_id = file_id
				else:
					forge_file_name, datafile_id = self.light_dictionary.get(file_id, forge_file_name)

		if forge_file_name is None:
			forge_file_name = next((fF for fF in self.pyUbiForge.forge_files.keys() if file_id in self.pyUbiForge.forge_files[fF].datafiles), None)
			if forge_file_name is None:
				forge_file_name, datafile_id = self.light_dictionary.get(file_id)
				if datafile_id is None:
					return
			else:
				datafile_id = file_id

		if not (file_id in self._temp_files and forge_file_name == self._temp_files[file_id][0] and datafile_id == self._temp_files[file_id][1]):
			self.pyUbiForge.forge_files[forge_file_name].decompress_datafile(datafile_id)
		self.refresh_usage(file_id)
		if file_id in self._temp_files and forge_file_name == self._temp_files[file_id][0] and datafile_id == self._temp_files[file_id][1]:
			return TempFile(
				self.pyUbiForge,
				forge_file_name,
				datafile_id,
				file_id,
				f'{self._temp_files[file_id][2]:08X}',
				self._temp_files[file_id][3],
				self._temp_files[file_id][4]
			)
		else:
			return

	def clear(self):
		"""Resets the TempFilesContainer class back to its starting state.
		Used when opening loading a new game.
		"""
		if self.light_dictionary.changed:
			self.save()
		self.light_dictionary.clear()
		self._memory = 0
		self._temp_files.clear()
		self._last_used.clear()

	def refresh_usage(self, file_id: int):
		"""Mark file_id as recently used so that it is not unloaded if the memory limit is reached."""
		if file_id in self._temp_files:
			self._last_used.remove(file_id)
		self._last_used.append(file_id)

	def save(self):
		self.light_dictionary.save()

	def load(self):
		self.light_dictionary.load()
