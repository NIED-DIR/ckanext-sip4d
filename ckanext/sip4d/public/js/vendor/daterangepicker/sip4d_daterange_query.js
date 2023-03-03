this.ckan.module('sip4ddaterange_query', function ($, _) {
    return {
        options: {
            ja : {
                autoUpdateInput: false,
                "locale": {
                    format: "YYYY/MM/DD",
                    separator: " - ",
                    applyLabel: '検索',
                    cancelLabel: '取消',
                    fromLabel: '開始',
                    toLabel: '終了',
                    customRangeLabel: "日時指定",
                    weekLabel: "W",
                    daysOfWeek: ["日","月","火","水","木","金","土"],
                    monthNames: ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"],
                    firstDay: 1
                },
                startDate: moment().startOf('day'),
                endDate: moment().startOf('day'),
                showDropdowns: true,
                timePicker: true
            },
            en : {
                autoUpdateInput: false,
                "locale": {
                    format: "MM/DD/YYYY",
                    separator: " - ",
                    applyLabel: "Apply",
                    cancelLabel: "Cancel",
                    fromLabel: "From",
                    toLabel: "To",
                    customRangeLabel: "Custom",
                    weekLabel: "W",
                    daysOfWeek: ["Su","Mo","Tu","We","Th","Fr","Sa"],
                    monthNames: ["January","February","March","April","May","June","July","August","September","October","November","December"],
                    firstDay: 1
                },
                startDate: moment().startOf('day'),
                endDate: moment().startOf('day'),
                showDropdowns: true,
                timePicker: true
            }
        },
        initialize: function() {
            var module = this;
            var lang = this.el.data('lang');

            var form = $(".search-form");
            if ($("#ext_startdate").length === 0) {
                $('<input type="hidden" id="ext_startdate" name="ext_startdate" />').appendTo(form);
            }
            if ($("#ext_enddate").length === 0) {
                $('<input type="hidden" id="ext_enddate" name="ext_enddate" />').appendTo(form);
            }

            let ext_startdate = null;
            let ext_enddate = null;
            if(getURLParameter("ext_startdate")) {
                ext_startdate = new Date(getURLParameter("ext_startdate"));
                var offset = ext_startdate.getTimezoneOffset();
                ext_startdate.setMinutes(ext_startdate.getMinutes() + offset);
                var iso_start = getURLParameter("ext_startdate");
                $('#ext_startdate').val(iso_start);
                var startDateString = getURLParameter("ext_startdate");
                $('#ext_startdate_after').text(startDateString);
            }
            if(getURLParameter("ext_enddate")) {
                ext_enddate = new Date(getURLParameter("ext_enddate"));
                var offset = ext_enddate.getTimezoneOffset();
                ext_enddate.setMinutes(ext_enddate.getMinutes() + offset);
                var iso_end = getURLParameter("ext_enddate");
                $('#ext_enddate').val(iso_end);
                var endDateString = getURLParameter("ext_enddate");
                $('#ext_enddate_after').text(endDateString);
            }

            var datelocation = module.options.en;
            if ('ja'===lang) {
                datelocation = module.options.ja;
            }
            if (ext_startdate!=null) {
                datelocation.startDate = ext_startdate;
            }
            if (ext_enddate!=null) {
                datelocation.endDate = ext_enddate;
            }

            $('input[id="daterange"]').daterangepicker(
                datelocation,
            );
            $('input[id="daterange"]').on('apply.daterangepicker', function(ev, picker) {
                if ('ja'===lang) {
                    $(this).val(picker.startDate.format('YYYY/MM/DD') + ' - ' + picker.endDate.format('YYYY/MM/DD'));
                } else {
                    $(this).val(picker.startDate.format('MM/DD/YYYY') + ' - ' + picker.endDate.format('MM/DD/YYYY'));
                }
                start = picker.startDate.format('YYYY-MM-DDTHH:mm:ss') + 'Z';
                end = picker.endDate.format('YYYY-MM-DDTHH:mm:ss') + 'Z';
                $('#ext_startdate').val(start);
                $('#ext_enddate').val(end);
                $(".search-form").submit();
            });
            $('input[id="daterange"]').on('cancel.daterangepicker', function(ev, picker) {
                $(this).val('');
            });

            function getURLParameter(name) {
                return decodeURIComponent((new RegExp('[?|&]' + name + '=' + '([^&;]+?)(&|#|;|$)').exec(location.search)||[,""])[1].replace(/\+/g, '%20'))||null;
            }
        }
    }
});
