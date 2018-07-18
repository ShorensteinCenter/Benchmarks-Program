# Flattens a nested dictionary
def flatten(input):
	output = {}
	for k, v in input.items():
		if isinstance(v, dict):
			output.update(flatten(v))
		else:
			output[k] = v
	return output