import os, re, json
from requests import Session
from zipfile import ZipFile, ZIP_STORED

class HttpFileError(Exception):
	pass

class Seekable:
	def seekable(self):
		return True

	def tell(self):
		return self._pos

	def seek(self, offset, whence=0):
		match whence:
			case 0:
				self._pos = offset
			case 1:
				self._pos += offset
			case 2:
				self._pos = self._file_size + offset
			case _:
				raise ValueError(f"whence {whence} is invalid")

# Open an HTTP URL as a seekable file
class HttpFile(Seekable):
	def __init__(self, url, debug=False):
		self.session = Session()
		self._url = url
		self.debug = debug
		self._pos = 0
		self._file_size = None
		self._total_read = 0
		self._request_count = 0

	def _request_range(self, start:int, end:int):
		if self.debug:
			print("HttpFile requested range:", start, end)
		if start < 0:
			byte_range = str(start)
		else:
			byte_range = "%d-%d" % (start, end)
		response = self.session.get(
			self._url,
			headers = {
				"Range": "bytes=" + byte_range
				}
			)
		if response.url != self._url:
			if self.debug:
				print(f" Redirected to: {response.url}")
			self._url = response.url
		if response.status_code == 206:
			content_length = int(response.headers["Content-Length"])
			m = re.match(r"^bytes (\d+)-(\d+)/(\d+)$", response.headers["Content-Range"])
			assert m
			start, stop, filesize = map(int, m.groups())
			if self.debug:
				print(f" Received range: {start}-{stop} ({content_length} bytes), filesize is {filesize}")
			self._file_size = filesize
		elif response.status_code == 200:
			raise HttpFileError("Server does not support range requests")
		else:
			raise HttpFileError("Fetch failed: %s" % response.status_code)
		data = response.content
		self._request_count += 1
		self._total_read += len(data)
		return data

	def seek(self, offset, whence=0):
		if whence == 2 and self._file_size is None:
			self._request_range(start = 0, end = 0)
		return super().seek(offset, whence)

	def read(self, size:int=None):
		if self.debug:
			print(f"HttpFile read {self._pos} {size}")
		if size is None:
			assert self._file_size is not None, "read() size must be specified until file size is known"
			size = (self._file_size - self._pos)
		data = self._request_range(
			start = self._pos,
			end = self._pos + size - 1,
			)
		self._pos += len(data)
		return data

	def close(self):
		if self.debug and self._file_size is not None:
			percent = int(self._total_read * 100 / self._file_size + 0.5)
			print(f"HttpFile close: {self._request_count} requests read {self._total_read} of {self._file_size} bytes ({percent}%)")
		self.session = None

# Disk cache which we can wrap around HttpFile
class FileCache(Seekable):
	blocksize = 256 * 1024
	def __init__(self, fh, cachedir, cachekey, debug=False):
		self.fh = fh
		self.cachedir = cachedir
		self.cachekey = cachekey
		self.debug= debug
		self.cache = {}
		self._pos = 0
		self._file_size = None
		self._metadata_file = os.path.join(self.cachedir, f"{self.cachekey}.json")

		try:
			with open(self._metadata_file) as fh:
				metadata = json.load(fh)
			self._file_size = self.fh._file_size = metadata["file-size"]
		except FileNotFoundError:
			pass

	def seek(self, offset, whence=0):
		if self.debug:
			print(f"FileCache seek({offset}, {whence})")
		if self._file_size is None and whence != 0:
			self._get_block(0, use_cache=False)
			self._file_size = self.fh._file_size
		super().seek(offset, whence)

	def read(self, size:int=None):
		if self.debug:
			print(f"FileCache read({size})")

		if size is None:
			assert self._file_size is not None, "read() size must be specified until file size is known"
			size = (self._file_size - self._pos)

		b1, b1first = self._addr_split(self._pos)
		if self.debug:
			print("b1:", b1, b1first)
		b2, b2last = self._addr_split(self._pos + size - 1)
		if self.debug:
			print("b2:", b2, b2last)

		if b1 == b2:
			data = self._get_block(b1)[b1first:b2last+1]
		else:
			blocks = [self._get_block(b1)[b1first:]]
			for blocknum in range(b1+1, b2):
				if self.debug:
					print("middle block:", blocknum)
				blocks.append(self._get_block(blocknum))
			blocks.append(self._get_block(b2)[:b2last+1])
			data = b"".join(blocks)

		assert len(data) == size, "FileCache read(%d) yielded %d bytes" % (size, len(data))
		self._pos += size
		self._file_size = self.fh._file_size
		return data

	def _addr_split(self, offset:int):
		return (offset // self.blocksize, offset % self.blocksize)

	def _get_block(self, blocknum:int, use_cache:bool=True):
		block = self.cache.get(blocknum)
		if block is None:
			cachefile = os.path.join(self.cachedir, f"{self.cachekey}-{blocknum:04d}")

			if use_cache:
				try:
					with open(cachefile, "rb") as fh:
						block = fh.read()
				except FileNotFoundError:
					pass

			if block is None:
				self.fh.seek(blocknum * self.blocksize)
				block = self.fh.read(self.blocksize)
				with open(cachefile, "wb") as fh:
					fh.write(block)

			self.cache[blocknum] = block
		return block

	def close(self):
		with open(self._metadata_file, "w") as fh:
			json.dump({"file-size": self._file_size}, fh)
		self.fh.close()

# A seekable file-like object which represents a byte range offset into another file-like object
class FileRange(Seekable):
	def __init__(self, fh, offset, size):
		self._fh = fh
		self._offset = offset
		self._file_size = size
		self._pos = 0

	def read(self, size=None):
		if size is None:
			size = (self._file_size - self._pos)
		self._fh.seek(self._offset + self._pos)
		data = self._fh.read(size)
		assert len(data) == size
		self._pos += size
		return data

# Add a function to ZipFile to open an embedded zip file, provided it does
# not use additional compression.
class EmbeddedZipMixin:
	def open_zipfile(self, filename):
		"""Open an embedded zip file"""
		if self.debug:
			print(f"Opening {filename}...")

		# We tried this first, but it immediately reads the whole file embedded zipfile
		# multiple times as soon as it is called. Bug in ZipFile?
		#zipfile = self.zipreader.open(filename)

		# Instead we find the offset of the embedded zipfile and create a view file handle
		info = self.getinfo(filename)
		assert info.compress_type == ZIP_STORED
		zipfile = FileRange(self.fh,
			offset = info.header_offset + len(info.FileHeader()),
			size = info.file_size,
			)

		if self.debug:
			print("Wrapping contents in Zipfile...")
		zipfile = ZipFile(zipfile)

		if self.debug:
			print("Wrapped.")
		return zipfile

# Same interface as RemoteZip, but for local file access.
class LocalZip(ZipFile, EmbeddedZipMixin):
	def __init__(self, path, debug=False):
		self.fh = open(path, "rb")
		self.debug = debug
		super().__init__(self.fh)
	def close(self):
		self.fh.close()

# Subclass ZipFile from the Python Standard Library so that we can
# read zip files over HTTP rather than from the file system.
class RemoteZip(ZipFile, EmbeddedZipMixin):
	def __init__(self, url, cachedir=None, cachekey=None, debug=False):
		self.debug = debug
		self.fh = HttpFile(url, debug=debug)
		self.fh = FileCache(self.fh, cachedir, cachekey, debug=debug)
		super().__init__(self.fh)
	def close(self):
		self.fh.close()
