import io, sys

path = '/root/marfagenez/core/src/life.rs'
test = open('/root/marfagenez/core/src/_exp79_test.rs', encoding='utf-8').read()
src = open(path, encoding='utf-8').read()

marker = '    #[test]\n    fn empty_population_is_refused() {'
if marker not in src:
    sys.exit('marker not found')
if 'exp79_the_poor_cell_organism_decides_to_move' in src:
    sys.exit('already inserted')

src = src.replace(marker, test + '\n' + marker, 1)
open(path, 'w', encoding='utf-8').write(src)
print('inserted')
