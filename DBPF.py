

# Python 3!

import io
from timeit import default_timer as timer

class SimsGame:
    Unknown = 0
    TS2 = 1
    TS3 = 2
    TS4 = 4

class MadScience:

    def _read_bytes(self, amount=1):
        return self.stream.read(amount)

    def _read_many(self, amount):
        return self.stream.read(amount)

    def _dword(self):
        return int.from_bytes(self.stream.read(4), byteorder='little')

    def _word(self):
        return int.from_bytes(self.stream.read(2), byteorder='little', signed=True)

    def _uword(self):
        return int.from_bytes(self.stream.read(2), byteorder='little', signed=False)

    def _hex(self):
        return '{0:0{1}X}'.format(self._dword(), 8)

    def _skip(self, amount):
        self.stream.seek(amount, 1)

    stream = None

class TGIKey(MadScience):

    typeId = '00000000'
    groupId = '00000000'
    instanceId = '00000000'

    order = 'TGI'
    hiInstance = False
    ppv = {
        't': None,
        'g': None,
        'i': None
    }
    reversedInstance = False

    def __init__(self, stream=None, hiInstance=False, ppv=None, reversedInstance=False):
        if stream is not None:
            self.stream = stream
            self.hiInstance = hiInstance
            if ppv is not None:
                self.ppv = ppv
            self.reversedInstance = reversedInstance
            self.load()
        pass

    def _read_instance(self):
        instance = self._hex()
        instance2 = ''

        if self.ppv['i'] is not None:
            instance2 = self.ppv['i']
        else:
            if self.hiInstance:
                instance2 = self._hex()

        if self.reversedInstance:
            return instance2 + instance

        return instance + instance2
    def load(self, stream=None):
        if stream is not None:
            self.stream = stream

        if self.order == 'TGI':
            self.typeId = self.ppv['t'] if self.ppv['t'] is not None else self._hex()
            self.groupId = self.ppv['g'] if self.ppv['g'] is not None else self._hex()
            self.instanceId = self._read_instance()

    def __str__(self):
        return self.typeId + ':' + self.groupId + ':' + self.instanceId



class DBPFHeader(MadScience):

    majorVersion = 0
    minorVersion = 0
    indexMajorVersion = 0
    indexMinorVersion = 0

    indexCount = 0
    indexOffset = 0
    indexSize = 0

    holesCount = 0
    holesOffset = 0
    holesSize = 0

    hiInstance = False

    game = SimsGame.Unknown

    def __init__(self, stream=None):
        if stream is not None:
            self.stream = stream
            self.load()
        pass

    # Used for majorVersion = 1 (aka TS2) headers
    def _read_header1(self):

        self._skip(20)

        self.indexMajorVersion = self._dword()
        self.indexCount = self._dword()
        self.indexOffset = self._dword()
        self.indexSize = self._dword()

        self.holesCount = self._dword()
        self.holesOffset = self._dword()
        self.holesSize = self._dword()
        self.indexMinorVersion = self._dword() - 1
        self._skip(32)

        self.game = SimsGame.TS2


    # Used for majorVersion = 2 (aka TS3) headers
    def _read_header2(self):
        self._skip(24)
        self.indexCount = self._dword()
        self._skip(4)
        self.indexSize = self._dword()
        self._skip(12)
        self.indexMajorVersion = self._dword()
        self.indexOffset = self._dword()
        self._skip(28)

        if self.minorVersion == 0:
            self.game = SimsGame.TS3
        if self.minorVersion == 1:
            self.game = SimsGame.TS4

        if self.indexMajorVersion == 3:
            self.hiInstance = True

    def load(self, stream=None):

        if stream is not None:
            self.stream = stream

        self.majorVersion = self._dword()
        self.minorVersion = self._dword()

        if self.majorVersion == 1:
            self._read_header1()
        else:
            self._read_header2()

        if self.indexMajorVersion == 7 and self.indexMinorVersion == 1:
            self.hiInstance = True

    def __str__(self):
        members = [attr for attr in dir(self) if not callable(getattr(self, attr)) and not attr.startswith("__")]
        ret = 'DBPFHeader class:\n'
        for m in members:
            ret += '\t' + m + ': ' + str(getattr(self, m)) + '\n'
        return ret


class DBPF(MadScience):

    presentPackageValues = {
        't': None,
        'g': None,
        'i': None
    }

    indexEntries = {}

    def __init__(self, stream=None):
        if stream is not None:
            self.stream = stream
            self.load()
        pass

    def load(self, stream=None, offset=0):

        if stream is not None:
            self.stream = stream

        tag = self._read_many(4)
        print(tag)

        header = DBPFHeader(self.stream)
        print(header)

        # Jump to offset
        self.stream.seek(offset + header.indexOffset)

        # Read in PPV if applicable
        if header.majorVersion == 2:
            ppv = self._dword()
            hasPackageTypeId = (ppv & (1 << 0)) == 1 << 0;
            hasPackageGroupId = (ppv & (1 << 1)) == 1 << 1;
            hasPackageInstanceId = (ppv & (1 << 2)) == 1 << 2;

            if hasPackageTypeId:
                self.presentPackageValues['t'] = self._hex()
            if hasPackageGroupId:
                self.presentPackageValues['g'] = self._hex()
            if hasPackageInstanceId:
                self.presentPackageValues['i'] = self._hex()

        dirResource = None

        start = timer()
                # Loop through index and read it in
        for i in range(header.indexCount):
            # Read in the TGI
            entry = {}
            entry['key'] = TGIKey(self.stream, ppv=self.presentPackageValues, hiInstance=header.hiInstance)

            entry['offset'] = self._dword()
            entry['filesize'] = self._dword()
            entry['compressed'] = False
            entry['truesize'] = 0
            entry['compressionFlags'] = 0
            entry['flags'] = 0

            if header.majorVersion == 2:
                entry['truesize'] = self._dword()
                if entry['filesize'] & 0x80000000 == 0x80000000:
                    entry['filesize'] -= 0x80000000

                    if header.minorVersion == 1:
                        entry['flags'] = self._uword()
                        entry['compressionFlags'] = self._word()
                    else:
                        entry['compressionFlags'] = self._word()
                        entry['flags'] = self._uword()

            if entry['compressionFlags'] != 0 and entry['compressionFlags'] != -1:
                if header.minorVersion != 1 and entry['compressionFlags'] != 1:
                    continue

            if entry['compressionFlags'] == -1 or entry['compressionFlags'] == 1:
                entry['compressed'] = True

            if entry['flags'] == 23106:
                entry['compressed'] = True

            self.indexEntries[str(entry['key'])] = entry

            if entry['key'].typeId == 'E86B1EEF':
                dirResource = entry

        end = timer()
        print(end - start)

        start = timer()

        # Read in DIR resource if applicable
        if dirResource is not None:
            self.stream.seek(offset + dirResource['offset'])
            # Figure out record size
            if header.indexMajorVersion == 7 and header.indexMinorVersion == 1:
                numRecords = int(dirResource['filesize'] / 20)
            else:
                numRecords = int(dirResource['filesize'] / 16)

            for i in range(numRecords):
                # Read each key in
                key = str(TGIKey(self.stream, ppv=self.presentPackageValues, hiInstance=header.hiInstance))
                filesize = self._dword()

                self.indexEntries[key]['compressed'] = True
                self.indexEntries[key]['truesize'] = filesize


        end = timer()
        print(end - start)


f = open("test.package", "rb")
dbpf = DBPF(f)
