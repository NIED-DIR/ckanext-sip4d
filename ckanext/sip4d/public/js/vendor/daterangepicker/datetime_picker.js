this.ckan.module('sip4d_informationdate_picker', function ($, _) {
    return {
        options: {
            ja : {
                autoUpdateInput: false,
                "locale": {
                    format: "YYYY-MM-DDThh:mm",
                    applyLabel: '設定',
                    cancelLabel: 'クリア',
                    weekLabel: "W",
                    daysOfWeek: ["日","月","火","水","木","金","土"],
                    monthNames: ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"],
                    firstDay: 1
                },
                singleDatePicker: true,
                startDate: moment().startOf('day'),
                endDate: moment().startOf('day'),
                showDropdowns: true,
                timePicker: true
            },
            en : {
                autoUpdateInput: false,
                "locale": {
                    format: "MM/DD/YYYY hh:mm",
                    applyLabel: "Apply",
                    cancelLabel: "Cancel",
                    weekLabel: "W",
                    daysOfWeek: ["Su","Mo","Tu","We","Th","Fr","Sa"],
                    monthNames: ["January","February","March","April","May","June","July","August","September","October","November","December"],
                    firstDay: 1
                },
                singleDatePicker: true,
                startDate: moment().startOf('day'),
                endDate: moment().startOf('day'),
                showDropdowns: true,
                timePicker: true
            }
        },
        initialize: function() {
            var module = this;
            var lang = this.el.data('lang');
            var datelocation = module.options.en;
            if ('ja'===lang) {
                datelocation = module.options.ja;
            }
            $('input[id="field-information_datetime"]').daterangepicker(
                datelocation,
            );
            $('input[id="field-information_datetime"]').on('apply.daterangepicker', function(ev, picker) {
                if ('ja'===lang) {
                    $(this).val(picker.startDate.format('YYYY-MM-DDTHH:mm'));
                } else {
                    $(this).val(picker.startDate.format('MM-DD-YYYYTHH:mm'));
                }
            });
            $('input[id="field-information_datetime"]').on('cancel.daterangepicker', function(ev, picker) {
                $(this).val('');
            });
        }
    }
});
