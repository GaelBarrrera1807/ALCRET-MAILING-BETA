import struct, zlib, requests

def make_png():
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xFFFFFFFF)
    ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + ihdr_crc
    raw = zlib.compress(b'\x00\xff\x00\x00')
    idat_crc = struct.pack('>I', zlib.crc32(b'IDAT' + raw) & 0xFFFFFFFF)
    idat = struct.pack('>I', len(raw)) + b'IDAT' + raw + idat_crc
    iend_crc = struct.pack('>I', zlib.crc32(b'IEND') & 0xFFFFFFFF)
    iend = struct.pack('>I', 0) + b'IEND' + iend_crc
    return sig + ihdr + idat + iend

# Login
resp = requests.post('http://localhost:8000/api/auth/login/', json={'username': 'admin', 'password': 'admin'})
print('Login:', resp.status_code)
if resp.status_code != 200:
    print(resp.text)
    exit(1)

token = resp.json()['access']

# Upload
png_data = make_png()
files = {'image': ('test.png', png_data, 'image/png')}
data = {'alt_text': 'test from curl'}
resp = requests.post('http://localhost:8000/api/mailer/images/', files=files, data=data, headers={'Authorization': f'Bearer {token}'})
print('Upload:', resp.status_code)
print('Response:', resp.json())
