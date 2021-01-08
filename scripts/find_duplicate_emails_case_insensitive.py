import csv
with open('accountsprod.csv') as csvfile:
    reader = csv.reader(csvfile)
    emails = [row[18] for row in reader]
with open('accountsprod.csv') as csvfile:
    reader = csv.reader(csvfile)
    emails_to_ids = {row[18]: row[0] for row in reader}

loweremails = [e.lower() for e in emails]
duplicates = [e for e in emails if loweremails.count(e.lower()) > 1]

duplicates_lower = list(set([e.lower() for e in duplicates]))


with open('childrenprod.csv') as csvfile:
    reader = csv.reader(csvfile)
    children_to_parent = {row[0]: row[2] for row in reader}


dup_lists = [[e for e in emails if e.lower() == dup] for dup in duplicates_lower]
for l in dup_lists:
    print(l)
    for e in l:
        print('\t' + e + ' (' + emails_to_ids[e] + ')')
        children = [c for (c,p) in children_to_parent.items() if p == emails_to_ids[e]]
        if children:
            print('\t\tchildren:')
            print('\t\t' + ', '.join(children))
        else:
            print('\t\tno children')
