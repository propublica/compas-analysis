from sys import stdout
from csv import DictReader, DictWriter


class PeekyReader:
    def __init__(self, reader):
        self.peeked = None
        self.reader = reader

    def peek(self):
        if self.peeked is None:
            self.peeked = next(self.reader)
        return self.peeked

    def __iter__(self):
        return self

    def __next__(self):
        if self.peeked is not None:
            ret = self.peeked
            self.peeked = None
            return ret
        try:
            return next(self.reader)
        except StopIteration:
            self.peeked = None
            raise StopIteration


class Person:
    def __init__(self, reader):
        self.__rows = []
        self.__idx = reader.peek()['id']
        try:
            while reader.peek()['id'] == self.__idx:
                self.__rows.append(next(reader))
        except StopIteration:
            pass

    @property
    def lifetime(self):
        memo = 0
        for it in self.__rows:
            memo += int(it['end']) - int(it['start'])
        return memo

    @property
    def recidivist(self):
        return (self.__rows[0]['is_recid'] == "1" and
                self.lifetime <= 730)

    @property
    def violent_recidivist(self):
        return (self.__rows[0]['is_violent_recid'] == "1" and
                self.lifetime <= 730)

    @property
    def low(self):
        return self.__rows[0]['score_text'] == "Low"

    @property
    def high(self):
        return not self.low

    @property
    def low_med(self):
        return self.low or self.score == "Medium"

    @property
    def true_high(self):
        return self.score == "High"

    @property
    def vlow(self):
        return self.__rows[0]['v_score_text'] == "Low"

    @property
    def vhigh(self):
        return not self.vlow

    @property
    def vlow_med(self):
        return self.vlow or self.vscore == "Medium"

    @property
    def vtrue_high(self):
        return self.vscore == "High"

    @property
    def score(self):
        return self.__rows[0]['score_text']

    @property
    def vscore(self):
        return self.__rows[0]['v_score_text']

    @property
    def race(self):
        return self.__rows[0]['race']

    @property
    def valid(self):
        return (self.__rows[0]['is_recid'] != "-1" and
                (self.recidivist and self.lifetime <= 730) or
                self.lifetime > 730)

    @property
    def compas_felony(self):
        return 'F' in self.__rows[0]['c_charge_degree']

    @property
    def score_valid(self):
        return self.score in ["Low", "Medium", "High"]

    @property
    def vscore_valid(self):
        return self.vscore in ["Low", "Medium", "High"]

    @property
    def rows(self):
        return self.__rows


def count(fn, data):
    return len(list(filter(fn, list(data))))


def t(tn, fp, fn, tp):
    surv = tn + fp
    recid = tp + fn
    print("           \tLow\tHigh")
    print("Survived   \t%i\t%i\t%.2f" % (tn, fp, surv / (surv + recid)))
    print("Recidivated\t%i\t%i\t%.2f" % (fn, tp, recid / (surv + recid)))
    print("Total: %.2f" % (surv + recid))
    print("False positive rate: %.2f" % (fp / surv * 100))
    print("False negative rate: %.2f" % (fn / recid * 100))
    spec = tn / (tn + fp)
    sens = tp / (tp + fn)
    ppv = tp / (tp + fp)
    npv = tn / (tn + fn)
    prev = recid / (surv + recid)
    print("Specificity: %.2f" % spec)
    print("Sensitivity: %.2f" % sens)
    print("Prevalence: %.2f" % prev)
    print("PPV: %.2f" % ppv)
    print("NPV: %.2f" % npv)
    print("LR+: %.2f" % (sens / (1 - spec)))
    print("LR-: %.2f" % ((1-sens) / spec))


def table(recid, surv, prefix=''):
    tn = count(lambda i: getattr(i, prefix + 'low'), surv)
    fp = count(lambda i: getattr(i, prefix + 'high'), surv)
    fn = count(lambda i: getattr(i, prefix + 'low'), recid)
    tp = count(lambda i: getattr(i, prefix + 'high'), recid)
    t(tn, fp, fn, tp)


def hightable(recid, surv, prefix=''):
    tn = count(lambda i: getattr(i, prefix + 'low_med'), surv)
    fp = count(lambda i: getattr(i, prefix + 'true_high'), surv)
    fn = count(lambda i: getattr(i, prefix + 'low_med'), recid)
    tp = count(lambda i: getattr(i, prefix + 'true_high'), recid)
    t(tn, fp, fn, tp)


def vtable(recid, surv):
    table(recid, surv, prefix='v')


def vhightable(recid, surv):
    hightable(recid, surv, prefix='v')


def is_race(race):
    return lambda x: x.race == race


def write_two_year_file(f, pop, test, headers):
    headers = list(headers)
    headers.append('two_year_recid')
    with open(f, 'w') as o:
        writer = DictWriter(o, fieldnames=headers)
        writer.writeheader()
        for person in pop:
            row = person.rows[0]
            if getattr(person, test):
                row['two_year_recid'] = 1
            else:
                row['two_year_recid'] = 0

            if person.compas_felony:
                row['c_charge_degree'] = 'F'
            else:
                row['c_charge_degree'] = 'M'
            writer.writerow(row)
            stdout.write('.')


def create_two_year_files():
    people = []
    headers = []
    with open("./cox-parsed.csv") as f:
        reader = PeekyReader(DictReader(f))
        try:
            while True:
                p = Person(reader)
                if p.valid:
                    people.append(p)
        except StopIteration:
            pass
        headers = reader.reader.fieldnames

    pop = list(filter(lambda i: (i.recidivist and i.lifetime <= 730) or
                      i.lifetime > 730,
                      filter(lambda x: x.score_valid, people)))

    vpop = list(filter(lambda i: (i.violent_recidivist and i.lifetime <= 730) or
                       i.lifetime > 730,
                       filter(lambda x: x.vscore_valid, people)))

    write_two_year_file("./compas-scores-two-years.csv", pop,
                        'recidivist', headers)
    write_two_year_file("./compas-scores-two-years-violent.csv", vpop,
                        'violent_recidivist', headers)


if __name__ == "__main__":
    create_two_year_files()
