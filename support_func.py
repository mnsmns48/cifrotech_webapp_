month = {
    '01': 'Январь',
    '02': 'Февраль',
    '03': 'Март',
    '04': 'Апрель',
    '05': 'Май',
    '06': 'Июнь',
    '07': 'Июль',
    '08': 'Август',
    '09': 'Сентябрь',
    '10': 'Октябрь',
    '11': 'Ноябрь',
    '12': 'Декабрь'
}

resolution_convert = lambda x: f"{x.split(' x ')[1]}x{x.split(' x ')[0]}"
month_convert = lambda n: f"{month.get(n.split('-')[1])} {n.split('-')[0]}"
name_cut = lambda n: n.rsplit(' ', maxsplit=2)[0].split(' ', maxsplit=1)[1]


def transfer(s: str) -> tuple:
    _list = list()
    _list.append(s.split(",")[0])
    _list.append(int(s.split(",")[1]))
    return tuple(_list)



