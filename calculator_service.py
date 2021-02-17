from party_model import Party
from party_names import *
from latest_surveys import *
import itertools
import pickle
import csv
import numpy
from collections import Counter
import copy
from progress.bar import Bar


from party_distribution import PartyDistribution


class CalculatorService:
    def __init__(self):
        self.successful_sum = 0
        self.party_list = {LIKUD: self.get_voting_distribution(LIKUD_SURVEY),
                           YESHATID: self.get_voting_distribution(YESHATID_SURVEY),
                           TIKVA: self.get_voting_distribution(TIKVA_SURVEY),
                           YEMINA: self.get_voting_distribution(YEMINA_SURVEY),
                           MESHUTEFET: self.get_voting_distribution(MESHUTEFET_SURVEY),
                           SHAS: self.get_voting_distribution(SHAS_SURVEY),
                           YAHADUT: self.get_voting_distribution(YAHADUT_SURVEY),
                           ISRAELBEITENU: self.get_voting_distribution(ISRAELBEITENU_SURVEY),
                           AVODA: self.get_voting_distribution(AVODA_SURVEY),
                           TZIYONUT: self.get_voting_distribution(TZIYONUT_SURVEY),
                           KAHOL: self.get_voting_distribution(KAHOL_SURVEY),
                           MERETZ: self.get_voting_distribution(MERETZ_SURVEY),
                           ZALICHA: self.get_voting_distribution(ZALICHA_SURVEY),
                           RAAM: self.get_voting_distribution(RAAM_SURVEY)}
        self.max_coalition_parties = []
        self.max_coalition_size = 0
        self.coalition = dict.fromkeys(range(16384), 0)
        self.coalition_plausibility = dict.fromkeys(range(16384), 0)
        self.get_possible_one_twenty(self.party_list)

    def get_possible_one_twenty(self, party_list):
        try:
            final_options = pickle.load(open("options.p", "rb"))
        except (OSError, IOError) as e:
            final_options = []
            delegates_list = []
            for party_key, party in party_list.items():
                delegates_list.append([x for x in party.keys()])
            for option in itertools.product(*delegates_list):
                if sum(list(option)) == 120:
                    final_options.append(list(option))
            pickle.dump(final_options, open("options.p", "wb"))

        self.total_options = len(final_options)
        with Bar('Processing', max=self.total_options) as bar:
            for optional_government in final_options:
                plaus_list = [self.party_list[x.name][x.delegates] for x in optional_government]
                plaus = numpy.product(plaus_list)
                parties = self.create_parties(optional_government)
                self.find_sixty_one(parties, [], 0, True, plaus)
                bar.next()
        self.clean_coalitions()
        self.save_data()


    def create_parties(self, delegates):
        party_list = [Party(LIKUD, delegates[0], [MESHUTEFET], 1),
                      Party(YESHATID, delegates[1], [MESHUTEFET, LIKUD, SHAS, YAHADUT], 2),
                      Party(TIKVA, delegates[2], [MESHUTEFET, LIKUD], 4),
                      Party(YEMINA, delegates[3], [MESHUTEFET, MERETZ, RAAM], 8),
                      Party(MESHUTEFET, delegates[4], [LIKUD, YEMINA, TZIYONUT, YAHADUT, SHAS], 16),
                      Party(SHAS, delegates[5], [MESHUTEFET, YESHATID], 32),
                      Party(YAHADUT, delegates[6], [MESHUTEFET, YESHATID], 64),
                      Party(ISRAELBEITENU, delegates[7], [MESHUTEFET, LIKUD, SHAS, YAHADUT], 128),
                      Party(AVODA, delegates[8], [LIKUD, TZIYONUT], 256)]
        if delegates[9] > 0:
            party_list.append(Party(TZIYONUT, delegates[9], [MESHUTEFET, MERETZ, RAAM], 512))
        if delegates[10] > 0:
            party_list.append(Party(KAHOL, delegates[10], [LIKUD, MESHUTEFET], 1024))
        if delegates[11] > 0:
            party_list.append(Party(MERETZ, delegates[11], [LIKUD, TZIYONUT], 2048))
        if delegates[12] > 0:
            party_list.append(Party(ZALICHA, delegates[12], [], 4096))
        if delegates[13] > 0:
            party_list.append(Party(RAAM, delegates[13], [TZIYONUT, YEMINA], 8192))
        return party_list


    def find_sixty_one(self, party_list_available: list, party_list_used: list, index: int, title_flag: bool, plausability: float):
        sum_parties = sum([x.delegates for x in party_list_used])
        if sum_parties > 60:
            if title_flag:
                self.successful_sum += 1
                title_flag = False
            if sum_parties > self.max_coalition_size:
                self.max_coalition_size = sum_parties
                self.max_coalition_parties = copy.deepcopy(party_list_used)
            coalition_hash = sum(x.hash for x in party_list_used)
            self.coalition[coalition_hash] += 1
            self.coalition_plausibility[coalition_hash] += plausability

        for i in range(index, len(party_list_available)):
            if self.possible_addition(party_list_available[i], party_list_used):
                party_list_used.append(party_list_available[i])
                self.find_sixty_one(party_list_available, party_list_used, i + 1, title_flag, plausability)
                party_list_used.pop(-1)
        return

    def possible_addition(self, party_checked, party_list_used: list):
        for p in party_list_used:
            if (party_checked.name in p.anti) or (p.name in party_checked.anti):
                return False
        return True

    def possible_split(self, party: Party):
        delegates = party.delegates
        return [round(0.4 * delegates), round(0.6 * delegates)]


    def clean_coalitions(self):
        for key, value in list(self.coalition.items()):
            if value == 0:
                del self.coalition[key]
                del self.coalition_plausibility[key]

    def get_parties_from_binary(self, num: int):
        parties = [LIKUD, YESHATID, TIKVA, YEMINA, MESHUTEFET, SHAS, YAHADUT, ISRAELBEITENU, AVODA, TZIYONUT, KAHOL,
                   MERETZ, ZALICHA, RAAM]
        return_parties = []
        while num != 0:
            if num % 2:
                return_parties.append(parties.pop(0))
            else:
                parties.pop(0)
            num = int(num / 2)
        return return_parties


    def get_voting_distribution(self, survey: list):
        distribution = numpy.random.normal(loc=numpy.nanmean(survey), scale=numpy.nanstd(survey), size=100000)
        round_dist = [round(x) for x in distribution]
        full_count = Counter(round_dist)
        zero_counter = 0
        for key, value in list(full_count.items()):
            full_count[key] = float(value / 10000)
            if key < 4:
                zero_counter += float(value / 10000)
                del full_count[key]
                continue
            if float(value / 10000) < 0.2:
                del full_count[key]
        if zero_counter > 0.2:
            full_count[0] = zero_counter
        return dict(full_count)

    def save_data(self):
        with open('coalition1.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            largest_coalition = ["Largest Coalition Parties"]
            largest_coalition.extend([x.name for x in self.max_coalition_parties])
            writer.writerow(largest_coalition)
            largest_coalition = ["Largest Coalition Delegates"]
            largest_coalition.extend([x.delegates for x in self.max_coalition_parties])
            largest_coalition.append(self.max_coalition_size)
            writer.writerow(largest_coalition)
            writer.writerow(["Successful Vote", self.successful_sum])
            writer.writerow(["Total Options Amount", self.total_options])
            for key in self.coalition.keys():
                line = [self.coalition[key], self.coalition_plausibility[key]]
                line.extend(self.get_parties_from_binary(key))
                writer.writerow(line)

