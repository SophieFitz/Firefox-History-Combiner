# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. 
# If a copy of the MPL was not distributed with this file, you can obtain one at http://mozilla.org/MPL/2.0/.

# This file re-implements the 'HashURL' function, see: https://searchfox.org/mozilla-central/source/toolkit/components/places/Helpers.cpp#269


from ctypes import c_uint32, c_uint64

maxCharsToHash = 1500
goldenRatioHex = c_uint32(0x9E3779B9).value

def add(currHash, currChar):
	currHash = goldenRatioHex * (((currHash << c_uint32(5).value) | (currHash >> c_uint32(27).value)) ^ c_uint32(ord(currChar)).value)
	return c_uint32(currHash).value

def getHash(url):
	maxLenToHash = min(len(url), maxCharsToHash)
	currHash = c_uint32(0).value
	finalHash = c_uint64(0).value
	
	for i in range(maxLenToHash):
		currHash = add(currHash, url[i])

	index = url.find(':', 0, 50)
	if index != -1:
		prefix = url[:index]
		prefixHash = c_uint64(0).value
		for i in range(len(prefix)):
			prefixHash = add(prefixHash, prefix[i])

		prefixHash = c_uint64(prefixHash & 0x0000FFFF).value
		finalHash = (prefixHash << 32) + currHash

	elif index == -1:
		finalHash = currHash

	return finalHash