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
        self.no_coalition_plause = 0
        self.yes_coalition_plause = 0
        self.total_options_plaus = 0
        self.max_coalition_parties = []
        self.max_coalition_size = 0
        self.coalition = dict.fromkeys(range(16384), 0)
        self.coalition_plausibility = dict.fromkeys(range(16384), 0)
        self.get_possible_one_twenty(self.party_list)

    # We get all of the possible combinations of party delegates and pick those that sum to 120
    def get_possible_one_twenty(self, party_list):
        try:
            final_options = pickle.load(open("options.pickle", "rb"))
        except (OSError, IOError) as e:
            final_options = []
            delegates_list = []
            for party_key, party in party_list.items():
                delegates_list.append([x for x in party.keys()])
            for option in itertools.product(*delegates_list):
                if sum(list(option)) == 120:
                    final_options.append(list(option))
            pickle.dump(final_options, open("options.pickle", "wb"))

        self.total_options = len(final_options)
        with Bar('Processing', max=self.total_options) as bar:
            for optional_government in final_options:
                all_parties, relevant_parties = self.create_parties(optional_government)
                plaus_list = [self.party_list[x.name][x.delegates] for x in all_parties]
                plaus = numpy.product(plaus_list)
                self.total_options_plaus += plaus
                if self.find_sixty_one(relevant_parties, [], 0, [], plaus):
                    self.successful_sum += 1
                    self.yes_coalition_plause += plaus
                else:
                    self.no_coalition_plause += plaus
                bar.next()
        self.clean_coalitions()
        self.save_data()


    def create_parties(self, delegates):
        party_list = [Party(LIKUD, delegates[0], [MESHUTEFET], 1),
                      Party(YESHATID, delegates[1], [LIKUD, SHAS, YAHADUT, TZIYONUT], 2),
                      Party(TIKVA, delegates[2], [MESHUTEFET, LIKUD], 4),
                      Party(YEMINA, delegates[3], [MESHUTEFET, RAAM], 8),
                      Party(MESHUTEFET, delegates[4], [LIKUD, YEMINA, TZIYONUT, YAHADUT, SHAS], 16),
                      Party(SHAS, delegates[5], [MESHUTEFET, YESHATID, RAAM], 32),
                      Party(YAHADUT, delegates[6], [MESHUTEFET, YESHATID, RAAM], 64),
                      Party(ISRAELBEITENU, delegates[7], [SHAS, YAHADUT], 128),
                      Party(AVODA, delegates[8], [LIKUD, TZIYONUT], 256),
                      Party(TZIYONUT, delegates[9], [MESHUTEFET, MERETZ, RAAM], 512),
                      Party(KAHOL, delegates[10], [LIKUD, MESHUTEFET], 1024),
                      Party(MERETZ, delegates[11], [LIKUD, TZIYONUT], 2048),
                      Party(ZALICHA, delegates[12], [], 4096),
                      Party(RAAM, delegates[13], [TZIYONUT, YEMINA], 8192)]
        relevant_parties = [party for party in party_list if party.delegates > 0]
        # if Isbak in Avoda - Bennet will not sit with them
        if party_list[8].delegates > 6:
            party_list[3].anti.append(AVODA)
        return party_list, relevant_parties


    def find_sixty_one(self, party_list_available: list, party_list_used: list, index: int, possible_coalition_flag: list, plausability: float):
        sum_parties = sum([x.delegates for x in party_list_used])
        if sum_parties > 60:
            if not possible_coalition_flag:
                possible_coalition_flag.append(True)
            if sum_parties > self.max_coalition_size:
                self.max_coalition_size = sum_parties
                self.max_coalition_parties = copy.deepcopy(party_list_used)
            coalition_hash = sum(x.hash for x in party_list_used)
            self.coalition[coalition_hash] += 1
            self.coalition_plausibility[coalition_hash] += plausability

        for i in range(index, len(party_list_available)):
            if self.possible_addition(party_list_available[i], party_list_used):
                party_list_used.append(party_list_available[i])
                self.find_sixty_one(party_list_available, party_list_used, i + 1, possible_coalition_flag, plausability)
                party_list_used.pop(-1)
        return len(possible_coalition_flag) > 0

    # We try to asses if a party is willing to sit with another party
    def possible_addition(self, party_checked, party_list_used: list):
        for p in party_list_used:
            if (party_checked.name in p.anti) or (p.name in party_checked.anti):
                return False
        return True

    # Todo: try to figure out split numbers
    def possible_split(self, party: Party):
        delegates = party.delegates
        return [round(0.4 * delegates), round(0.6 * delegates)]

    # remove options of coalition that did not workout.
    def clean_coalitions(self):
        for key, value in list(self.coalition.items()):
            if value == 0:
                del self.coalition[key]
                del self.coalition_plausibility[key]

    # unhashing
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
        sum_deleted = 0
        for key, value in list(full_count.items()):
            percent_value = float(value/100000)
            full_count[key] = percent_value
            if key < 4:
                zero_counter += percent_value
                del full_count[key]
                continue
            if percent_value < 0.01:
                sum_deleted += percent_value
                del full_count[key]
        if zero_counter > 0.01:
            full_count[0] = zero_counter
        # normalizing after deletions
        for key, value in list(full_count.items()):
            full_count[key] = 10*(value/(1-sum_deleted))
        return dict(full_count)

    def save_data(self):
        with open('coalition.csv', 'w', newline='') as file:
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
            writer.writerow(["Yes Coalition Chance", self.yes_coalition_plause / self.total_options_plaus])
            writer.writerow(["No Coalition Chance", self.no_coalition_plause / self.total_options_plaus])
            for key in self.coalition.keys():
                coalition_plausability = self.coalition_plausibility[key] / self.total_options_plaus
                line = [self.coalition[key], coalition_plausability * 100]
                line.extend(self.get_parties_from_binary(key))
                writer.writerow(line)

