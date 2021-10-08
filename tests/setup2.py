import unittest
from lib.csv_parser import Surveys
from lib.impact import get_property_actions

class TestImpactGen(unittest.TestCase):
    def flatten_impacts(self, impacts):
        ret = []
        for impact in impacts:
            for sdg in impact['sdgs']:
                ret.append('%s:%s'%(impact['pp'], sdg))

        return ret

    def base_positive_test(self, answers, property_code, facet_codes, expected_answers):
        impacts = get_property_actions(answers, property_code, facet_codes)
        combined_impacts = self.flatten_impacts(impacts)

        for impact in combined_impacts:
            self.assertTrue(impact in expected_answers)

        unexpected_answers = [x for x in combined_impacts if x not in expected_answers]
        self.assertEqual(len(unexpected_answers), 0)

        missing_answers = [x for x in expected_answers if x not in combined_impacts]
        self.assertEqual(len(missing_answers), 0)

    def base_negative_test(self, answers, property_code, facet_codes, expected_answers):
        impacts = get_property_actions(answers, property_code, facet_codes)
        combined_impacts = self.flatten_impacts(impacts)

        for impact in combined_impacts:
            self.assertFalse(impact in expected_answers)

    def test_energy_basic(self):
        facet_codes = ['F-1.2', 'F-3.2']

        property_code = 'X-1.1'
        answer_codes = ['X1-1']

        expected_answers = ['PP01.02:7.3', 'PP01.02:7.a']

        self.base_positive_test(answer_codes, property_code, facet_codes, expected_answers)

    def x_test_energy_1(self):
        facet_codes = ['F-1.1', 'F-4.1', 'F-3.2']

        property_code = 'X-1.1'
        answer_codes = ['X1-1', 'X1-2', 'X1-2.1', 'X1-2.2', 'X1-3']

        expected_answers = ['PP01.02:7.3', 'PP01.02:7.a', 'PP02.01:7.1', 'PP02.01:7.a', 'PP02.01:7.b', 'PP21.01:7.b', 'PP01.01:7.2', 'PP01.01:7.a']

        self.base_positive_test(answer_codes, property_code, facet_codes, expected_answers)

    def x_test_people_mutli_sdg(self):
        facet_codes = ['F-2.3']

        property_code = 'X-1.7'
        answer_codes = ['X7-3']

        expected_answers = ['PP19.03:10.2',  'PP19.03:16.10', 'PP19.03:5.1']

        self.base_positive_test(answer_codes, property_code, facet_codes, expected_answers)

    def x_test_people_facet_or(self):
        facet_codes = ['F-2.3']

        property_code = 'X-1.7'
        answer_codes = ['X7-3', 'X7-3.1']

        expected_answers = ['PP19.03:10.2',  'PP19.03:16.10', 'PP19.03:5.1', 'PP19.03:4.5']

        self.base_positive_test(answer_codes, property_code, facet_codes, expected_answers)

        facet_codes = ['F-2.4']
        expected_answers = ['PP19.03:5.1', 'PP19.03:4.5']

        self.base_negative_test(answer_codes, property_code, facet_codes, expected_answers)

    def x_test_gives_only_one_impact_back(self):
        """
        clicking all the way down to 3.1.2,
        should only give one impact
        ie, not an impact for 3.1 or 3
        """
        facet_codes = []
        property_code = 'X-1.7'
        answers = ['X7-3', 'X7-3.1', 'X7-3.1.2']
        # impacts = get_property_actions(answers, property_code, facet_codes)
        # print(impacts)

        # self.assertEqual(len(impacts), 1)
        # expected_answers = ['PP19.03:10.2',  'PP19.03:16.10', 'PP19.03:5.1', 'PP19.03:4.5']
        # self.base_positive_test(answer_codes, property_code, facet_codes, expected_answers)

    def x_test_energy_no_facets_option(self):
        """
        pick one, check it spits out the same
        """
        facet_codes = []
        property_code = 'X-1.1'
        answer_codes = ['X7-1']

        expected_action = 'PP01.02'
        expected_sdg = '7.3'

if __name__ == '__main__':
    unittest.main()
