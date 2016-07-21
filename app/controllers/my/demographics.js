import Ember from 'ember';

const {
    service
} = Ember.inject;

import validators from 'lookit-base/utils/validators';

export default Ember.Controller.extend({
    session: service('session'),
    sessionAccount: service('session-account'),
    selectedRaceIdentification: Ember.computed.alias('model.demographicsRaceIdentification'),
    today: new Date(),
    ageChoices: [
        'under 18',
        '18-21',
        '22-24',
        '25-29',
        '30-34',
        '35-39',
        '40-44',
        '45-49',
        '50-59',
        '60-69',
        '70 or over'
    ],
    childrenCounts: [
        '0',
        '1',
        '2',
        '3',
        '4',
        '5',
        '6',
        '7',
        '8',
        '9',
        '10',
        'More than 10'
    ],
    raceCategories: [
        'White',
        'Hispanic, Latino, or Spanish origin',
        'Black or African American',
        'Asian',
        'American Indian or Alaska Native',
        'Middle Eastern or North African',
        'Native Hawaiian or Other Pacific Islander',
        'Another race, ethnicity, or origin'
    ],
    genderOptions: [
        'male',
        'female',
        'other',
        'prefer not to answer'
    ],
    educationOptions: [
        'some or attending high school',
        'high school diploma or GED',
        'some or attending college',
        '2-year college degree',
        '4-year college degree',
        'some or attending graduate or professional school',
        'graduate or professional degree'
    ],
    spouseEducationOptions: [
        'some or attending high school',
        'high school diploma or GED',
        'some or attending college',
        '2-year college degree',
        '4-year college degree',
        'some or attending graduate or professional school',
        'graduate or professional degree',
        'not applicable - no spouse or partner'
    ],
    annualIncomeOptions: Ember.computed(function() {
        var ret = ['0', '5K'];
        for (var i = 10; i < 200; i += 10) {
            ret.push(`${i}K`);
        }
        ret.push('over 200K');
        ret.push('prefer not to answer');

        return ret;
    }),
    guardianOptions: [
        '1',
        '2',
        '3 or more',
        'varies'
    ],
    yesNoOptions: [
        'no answer',
        'yes',
        'no'
    ],

    isValid: Ember.computed('model.demographicsNumberOfBooks', function() {
        return validators.min(0)(this.get('model.demographicsNumberOfBooks'));
    }),

    nNumberOfChildren: 11,
    numberOfChildren: Ember.computed('nNumberOfChildren', 'model.demographicsNumberOfChildren', function() {
        var numberOfChildren = this.get('model.demographicsNumberOfChildren');
        if (!numberOfChildren) {
            return 0;
        } else if (isNaN(numberOfChildren)) {
            numberOfChildren = this.get('nNumberOfChildren');
            if (!numberOfChildren) {
                return 0;
            } else {
                return parseInt(numberOfChildren);
            }
        } else {
            return parseInt(numberOfChildren);
        }
    }),
    onNumberOfChildrenChange: Ember.observer('numberOfChildren', function() {
        var numberOfChildren = this.get('numberOfChildren');
        var birthdays = [];
        for (var i = 0; i < numberOfChildren; i++) {
            birthdays[i] = this.get('model.demographicsChildBirthdays').objectAt(i);
        }
        this.get('model.demographicsChildBirthdays').setObjects(birthdays);
    }),
    childBirthdays: Ember.computed('model.demographicsChildBirthdays.[]', {
        get: function() {
            var ret = Ember.Object.create();
            this.get('model.demographicsChildBirthdays').toArray().forEach(function(bd, i) {
                ret.set(i.toString(), bd);
            });
            return ret;
        },
        set: function(_, birthdays) {
            var ret = [];
            Object.keys(birthdays).forEach(function(key) {
                ret[parseInt(key)] = birthdays[key];
            });
            this.get('model.demographicsChildBirthdays').setObjects(ret);
            this.propertyDidChange('childBirthdays');
            return this.get('childBirthdays');
        }
    }),
    actions: {
        selectRaceIdentification: function(item) {
            var selectedRaceIdentification = this.get('selectedRaceIdentification') || [];
            if (item.checked) {
                if (selectedRaceIdentification.indexOf(item.value) === -1) {
                    selectedRaceIdentification.push(item.value);
                }
            } else {
                selectedRaceIdentification = selectedRaceIdentification.filter(i => i !== item.value);
            }
            this.set('selectedRaceIdentification', selectedRaceIdentification);
        },
        saveDemographicsPreferences: function() {
            this.get('model').save().then(() => {
                this.toast.info('Demographic survey saved successfully.');
            });
        },
        setChildBirthday(index, birthday) {
            var childBirthdays = this.get('childBirthdays');
            childBirthdays.set(index.toString(), birthday);
            this.set('childBirthdays', childBirthdays);
        }
    }
});
