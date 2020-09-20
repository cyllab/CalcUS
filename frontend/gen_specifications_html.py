from constants import SPECIFICATIONS

for software, keywords in SPECIFICATIONS.items():
    for k, d in keywords.items():
        for option, num in d.items():
            avail_str = 'software_specific avail_{}'.format(software)
            if k == 'opt':
                avail_str += ' type_specific avail_Geometrical_Optimisation avail_Constrained_Optimisation'
            elif k == 'freq':
                avail_str += ' type_specific avail_Frequency_Calculation'

            if num == 1:
                option_str = "has_value"
                _option = "{}({}=...)".format(k, option)
                _value = "{}({}=)".format(k, option)
            else:
                option_str = ""
                _option = "{}({})".format(k, option)
                _value = "{}({})".format(k, option)

            print("""<option value="{}" class="{} {}">{}</option>""".format(_value, avail_str, option_str, _option))
