import collections
import hashlib
import os
import re
import struct
import urllib.parse
import zlib
import codecs
# pylint: disable=unused-import
import pdb

# pylint: enable=unused-import

from http.client import HTTPSConnection


Commit = collections.namedtuple("Commit", ["parent", "tree"])
Delta = collections.namedtuple("Delta", ["objHash", "data"])
ObjTypeDict = {
    1: "commit",
    2: "tree",
    3: "blob",
    4: "tag",
    6: "offset_delta",
    7: "ref_delta",
}
def initRepo():
    os.mkdir(".git")
    os.mkdir(".git/objects")
    os.mkdir(".git/refs")
    with open(".git/HEAD", "w") as f:
        f.write("ref: refs/heads/master\n")

def objFilePath(objName):
    return os.path.join(".git", "objects", objName[0:2], objName[2:])

def readGitObj(objHash):
    data = None
    objType = None
    with codecs.open(objFilePath(objHash), 'r', encoding='zlib') as objFile:
        data = objFile.read()
        objType, _ = data.split(b' ', 1)
        _, data = data.split(b'\x00', 1) # strip header

    return objType.decode(), data

def writeGitObj(objContent, objType):
    sha1 = hashlib.sha1()

    header = b"%s %d\x00" % (objType.encode(), len(objContent))
    data = header + objContent
    sha1.update(data)

    objHash = sha1.hexdigest()
    path = objFilePath(objHash)
    dirPath = os.path.dirname(path)

    if not os.path.exists(dirPath):
        os.makedirs(dirPath)

    with codecs.open(path, 'w', encoding='zlib') as objFile:
        objFile.write(data)

    return objHash
def getMaster(url):
    urldata = urllib.parse.urlparse(url)
    req = HTTPSConnection("%s" % urldata.netloc)
    req.request("GET", "%s.git/info/refs?service=git-upload-pack" % urldata.path)
    resp = req.getresponse()
    refs = resp.read().decode().splitlines()

    masterHash = None
    refRe = re.compile("[a-z0-9]+ refs/heads/master")
    for r in refs:
        if refRe.match(r):
            masterHash, _ = r.split(" ")
            masterHash = masterHash[4:]
            break

    return masterHash


def downloadPack(url, masterHash):
    content = b"0032want %s\n" % masterHash.encode()
    content += b"0000"
    content += b"0009done\n"

    urldata = urllib.parse.urlparse(url)
    req = HTTPSConnection("%s" % urldata.netloc)
    req.request(
        "POST",
        "%s.git/git-upload-pack" % urldata.path,
        body=content,
        headers={"content-type": "x-git-upload-pack-request"},
    )
    resp = req.getresponse()
    data = resp.read()

    nak, pack = data.split(b"\n", 1)
    assert nak[4:] == b"NAK"

    return pack


def unpack(pack):
    assert pack[0:4] == b"PACK", "not a pack file"

    sha1 = hashlib.sha1()
    pack, packHash = pack[0:-20], pack[-20:]
    sha1.update(pack)
    assert sha1.digest() == packHash, "pack sha1 doesn't match"

    pack = pack[8:]  # skip header and version
    (objs,), pack = (
        struct.unpack("!I", pack[0:4]),
        pack[4:],
    )  # extract number of objects

    deltas = []
    for _ in range(objs):
        c, pack = pack[0], pack[1:]
        objType = ObjTypeDict[c >> 4 & 0x7]
        size = c & 0xF
        shift = 4
        while c & 0x80:
            c, pack = pack[0], pack[1:]
            size += (c & 0x7F) << shift
            shift += 7

        # decompress object
        decompressor = zlib.decompressobj()
        if objType in ["commit", "tree", "blob"]:
            raw = decompressor.decompress(pack, max_length=size)
            assert len(raw) == size
            decompressor.flush()
            writeGitObj(raw, objType)
        else:  # deltas
            deltaName, pack = pack[0:20], pack[20:]
            raw = decompressor.decompress(pack, max_length=size)
            decompressor.flush()
            assert len(raw) == size
            assert size >= 4
            deltas.append(Delta(objHash=deltaName.hex(), data=raw))
        pack = decompressor.unused_data

    return deltas


def parseInstruction(raw):
    instList = []
    while raw:
        instByte, raw = raw[0], raw[1:]
        instName = "copy" if instByte & 0x80 else "insert"
        if instName == "copy":
            offset = 0
            size = 0

            shift = 0
            offsetBits = instByte & 0xF
            while offsetBits:
                if offsetBits & 1:
                    offset |= raw[0] << shift
                    raw = raw[1:]
                shift += 8
                offsetBits = offsetBits >> 1

            shift = 0
            sizeBits = (instByte >> 4) & 0x7
            while sizeBits:
                if sizeBits & 1:
                    size |= raw[0] << shift
                    raw = raw[1:]
                shift += 8
                sizeBits = sizeBits >> 1

            size = size or 0x1000
            instList.append((instName, size, offset, None))
        else:
            size = instByte & 0x7F
            data, raw = raw[0:size], raw[size:]
            assert len(data) == size
            instList.append((instName, size, 0, data))

    return instList


def processVarInt(raw):
    shift = 0
    var = 0
    while raw[0] & 0x80:
        c, raw = raw[0], raw[1:]
        var |= (c & 0x7F) << shift
        shift += 7

    c, raw = raw[0], raw[1:]
    var += (c & 0x7F) << shift
    return var, raw


def processDelta(deltaList):
    for delta in deltaList:
        raw = delta.data

        # skip source and target length
        sourceSize, raw = processVarInt(raw)
        targetSize, raw = processVarInt(raw)

        instList = parseInstruction(raw)
        objType, content = readGitObj(delta.objHash)
        assert len(content) == sourceSize
        target = bytearray()
        for inst, size, offset, data in instList:
            if inst == "copy":
                assert offset + size <= sourceSize
                target += content[offset : offset + size]
            else:
                target += data

        assert len(target) == targetSize, "target: %d, actual: %d" % (
            targetSize,
            len(target),
        )
        writeGitObj(target, objType)


def parseCommit(commit):
    _, commitData = readGitObj(commit)
    tree = parent = None
    for line in commitData.decode().splitlines():
        if not line:
            break
        attr, value = line.split(" ", 1)
        if attr == "tree":
            tree = value
        elif attr == "parent":
            parent = value
    return Commit(parent=parent, tree=tree)


def writeCommitTree(treeHash, root):
    pwd = os.getcwd()
    os.chdir(root)
    _, treeData = readGitObj(treeHash)
    os.chdir(pwd)

    while treeData:
        mode, treeData = treeData.split(b" ", 1)
        name, treeData = treeData.split(b"\x00", 1)
        sha1, treeData = treeData[0:20], treeData[20:]

        mode = int(mode, 8)
        if mode & 0x4000:  # is dir
            if not os.path.exists(name):
                os.mkdir(name)
            os.chdir(name)
            writeCommitTree(sha1.hex(), root)
            os.chdir(pwd)
        else:
            os.chdir(root)
            _, blobData = readGitObj(sha1.hex())
            os.chdir(pwd)
            with open(name, "w") as f:
                f.write(blobData.decode())
            os.chmod(name, mode & 0x1FF)


def clone(url, directory):
    os.chdir(directory)
    masterHash = getMaster(url)
    initRepo()
    pack = downloadPack(url, masterHash)
    deltaList = unpack(pack)
    processDelta(deltaList)
    writeCommitTree(parseCommit(masterHash).tree, os.getcwd())
