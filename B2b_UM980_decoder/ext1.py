def extract_data_from_line(line):
    # Split each line by commas
    parts = line.split(',')

    # Check if there is enough data
    if len(parts) < 15:
        return None

    # Extract the required data
    week = parts[4]
    wn = str(int(parts[5]) // 1000)
    prn = str(int(parts[10]) - 160)
    iodssr = parts[11]
    iodp = parts[12]
    todbdt = parts[13]

    # Convert the 15th data element to binary, remove the part after '*',
    # and ensure the length is four times the original hexadecimal string length
    hex_data = parts[14].split('*')[0]
    binary_data = bin(int(hex_data, 16))[2:].zfill(len(hex_data) * 4)

    # Slice and extract data for different satellite systems
    bds = binary_data[:63]
    gps = binary_data[63:100]
    galileo = binary_data[100:137]
    glonass = binary_data[137:174]

    return f'week:{week} wn:{wn} prn:{prn} iodssr:{iodssr} iodp:{iodp} todbdt:{todbdt} BDS:{bds} GPS:{gps} Galileo:{galileo} GLONASS:{glonass}\n'

# 读取文件并逐行处理
with open('D:\\cssrlibccc\\src\\cssrlib\\msg1.txt', 'r') as file, open('D:\\cssrlibccc\\src\\cssrlib\\bdsmsg1.txt', 'w') as output_file:
    for line in file:
        data = extract_data_from_line(line)
        if data:
            output_file.write(data)



