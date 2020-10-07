from constants import SPECIFICATIONS

for k, d in SPECIFICATIONS['Gaussian'].items():
    for option, num in d.items():
        avail_str = 'software_specific avail_Gaussian'
        if k == 'opt':
            avail_str += ' type_specific avail_Geometrical_Optimisation avail_Constrained_Optimisation avail_TS_Optimisation'
        elif k == 'freq':
            avail_str += ' type_specific avail_Frequency_Calculation'

        if k == "general":
            _option = option
            _value = option
            option_str = ""
        else:
            if num == 1:
                option_str = "has_value"
                _option = "{}({}=...)".format(k, option)
                _value = "{}({}=)".format(k, option)
            else:
                option_str = ""
                _option = "{}({})".format(k, option)
                _value = "{}({})".format(k, option)

        print("""<option value="{}" class="{} {}">{}</option>""".format(_value, avail_str, option_str, _option))

for section, d in SPECIFICATIONS['ORCA'].items():
    for k, num in d.items():
        avail_str = 'software_specific avail_ORCA'
        if section == 'opt':
            avail_str += ' type_specific avail_Geometrical_Optimisation avail_Constrained_Optimisation avail_TS_Optimisation'
        if num == 1:
            option_str = " has_value"
            _option = "{}...".format(k)
            _value = k
        else:
            option_str = ""
            _option = k
            _value = k

        print("""<option value="{}" class="{}{}">{}</option>""".format(_value, avail_str, option_str, _option))

for section, d in SPECIFICATIONS['xtb'].items():
    for k, num in d.items():
        avail_str = 'software_specific avail_xtb'
        if section == 'Geometrical Optimisation':
            avail_str += ' type_specific avail_Geometrical_Optimisation avail_Constrained_Optimisation avail_TS_Optimisation'
        elif section == 'Conformational Search':
            avail_str += ' type_specific avail_Conformational_Search avail_Constrained_Conformational_Search'

        if num == 1:
            option_str = " has_value"
            _option = "{}=...".format(k)
            _value = "{}=".format(k)
        else:
            option_str = ""
            _option = k
            _value = k

        print("""<option value="{}" class="{}{}">{}</option>""".format(_value, avail_str, option_str, _option))
