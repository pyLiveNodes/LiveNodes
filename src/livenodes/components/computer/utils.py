

def parse_location(location):
    comps = ['', '', '', '']
    
    splits = location.split(':')
    for i, split in enumerate(reversed(splits)):
        comps[i] = split

    thread, process, port, host = comps        
    host = f"{host}:{port}"

    return host, process, thread