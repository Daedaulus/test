@staticmethod
def _split_description(description):
    match = re.findall(r'[0-9]+', description)
    return int(match[0]) * 1024 ** 2, int(match[1]), int(match[2])
