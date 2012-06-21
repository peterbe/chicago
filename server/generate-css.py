DECK = [x + y for x in
        [str(x) for x in range(2, 11)] + list('JQKA')
        for y in list('SCDH')]


for j, each in enumerate(list('CDHS')):
    for i, card in enumerate(['A'] + [str(x) for x in range(2, 11)] + list('JQK')):
        print ('.c%s { background-position: -%dpx -%dpx }' %
            ((card+each).ljust(3), 79 * i, 123 * j))
