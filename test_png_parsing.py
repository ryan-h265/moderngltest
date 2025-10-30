#!/usr/bin/env python3
"""
Standalone PNG parsing diagnostic test.
Tests if PNG files in the assets directory can be parsed correctly.
"""

from pathlib import Path
import struct
import zlib

PROJECT_ROOT = Path(__file__).parent

def test_png_parsing():
    """Test PNG parsing on all PNG files in assets."""

    # Check lights directory
    lights_dir = PROJECT_ROOT / "assets" / "ui" / "thumbs" / "lights"
    models_dir = PROJECT_ROOT / "assets" / "ui" / "thumbs" / "models"

    print("=" * 60)
    print("PNG PARSING DIAGNOSTIC TEST")
    print("=" * 60)

    for category, directory in [("Lights", lights_dir), ("Models", models_dir)]:
        print(f"\n[{category}]")
        print(f"Directory: {directory}")
        print(f"Exists: {directory.exists()}")

        if not directory.exists():
            print(f"  ✗ Directory not found!")
            continue

        png_files = list(directory.glob("*.png"))
        print(f"Found {len(png_files)} PNG files")

        for png_file in png_files:
            print(f"\n  File: {png_file.name}")
            print(f"    Size: {png_file.stat().st_size} bytes")

            try:
                png_data = png_file.read_bytes()

                # Check PNG signature
                if png_data[:8] != b'\x89PNG\r\n\x1a\n':
                    print(f"    ✗ Invalid PNG signature")
                    continue

                print(f"    ✓ Valid PNG signature")

                # Parse IHDR chunk
                offset = 8
                width = height = None

                # Read length and type
                chunk_length = struct.unpack('>I', png_data[offset:offset+4])[0]
                chunk_type = png_data[offset+4:offset+8].decode('ascii')

                print(f"    First chunk: {chunk_type} (length: {chunk_length})")

                if chunk_type == 'IHDR':
                    # Parse IHDR - should be 13 bytes
                    ihdr_data = png_data[offset+8:offset+8+13]
                    if len(ihdr_data) >= 13:
                        width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                            '>IIBBBBB', ihdr_data[:13]
                        )
                        print(f"    ✓ IHDR parsed successfully")
                        print(f"      - Dimensions: {width}x{height}")
                        print(f"      - Bit depth: {bit_depth}")
                        print(f"      - Color type: {color_type} (0=Gray, 2=RGB, 3=Indexed, 4=Gray+Alpha, 6=RGBA)")
                        print(f"      - Compression: {compression}")
                        print(f"      - Filter: {filter_method}")
                        print(f"      - Interlace: {interlace}")
                    else:
                        print(f"    ✗ IHDR too short: {len(ihdr_data)} bytes (need 13)")
                else:
                    print(f"    ✗ First chunk is not IHDR")

                # Try to find IDAT chunks
                offset = 8
                idat_chunks = []
                while offset < len(png_data) - 8:
                    if offset + 8 > len(png_data):
                        break
                    chunk_length = struct.unpack('>I', png_data[offset:offset+4])[0]
                    chunk_type = png_data[offset+4:offset+8].decode('ascii', errors='ignore')

                    if chunk_type == 'IDAT':
                        chunk_data = png_data[offset+8:offset+8+chunk_length]
                        idat_chunks.append(chunk_data)

                    offset += 12 + chunk_length  # 4 (len) + 4 (type) + data + 4 (crc)

                if idat_chunks:
                    print(f"    ✓ Found {len(idat_chunks)} IDAT chunks")
                    idat_data = b''.join(idat_chunks)
                    print(f"      Total IDAT size: {len(idat_data)} bytes")

                    # Try decompression
                    try:
                        decompressed = zlib.decompress(idat_data)
                        print(f"      ✓ Successfully decompressed to {len(decompressed)} bytes")
                    except Exception as e:
                        print(f"      ✗ Decompression failed: {e}")
                else:
                    print(f"    ✗ No IDAT chunks found!")

            except Exception as e:
                print(f"    ✗ Error: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_png_parsing()
