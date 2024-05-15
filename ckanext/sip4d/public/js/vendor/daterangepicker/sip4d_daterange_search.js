this.ckan.module('sip4ddaterange_search', function ($, _) {
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
            // データセットの日時検索を行う
            if ($("#ext_startdate").length === 0) {
                $('<input type="hidden" id="ext_startdate" name="ext_startdate" />').appendTo(form);
            }
            if ($("#ext_enddate").length === 0) {
                $('<input type="hidden" id="ext_enddate" name="ext_enddate" />').appendTo(form);
            }
            if ($("#ext_limit").length === 0) {
                $('<input type="hidden" id="ext_limit" name="limit" />').appendTo(form);
            }
            // 検索対象の日時情報 information_date:情報日時 metadata_modified:更新日時 search_type_created:作成日時
            if ($("#ext_search_date_type").length === 0) {
                $('<input type="hidden" id="ext_search_date_type" name="ext_search_date_type" />').appendTo(form);
            }

            var ext_startdate = null;
            var ext_enddate = null;
            let search_type = null;
            if ( getURLParameter("ext_startdate")) {
                ext_startdate = new Date(getURLParameter("ext_startdate"));
                var offset = ext_startdate.getTimezoneOffset();
                ext_startdate.setMinutes(ext_startdate.getMinutes() + offset);
                var iso_start = getURLParameter("ext_startdate");//ext_startdate.toISOString();
                $('#ext_startdate').val(iso_start);
            }
            if (getURLParameter("ext_enddate")) {
                ext_enddate = new Date(getURLParameter("ext_enddate"));
                var offset = ext_enddate.getTimezoneOffset();
                ext_enddate.setMinutes(ext_enddate.getMinutes() + offset);
                var iso_end = getURLParameter("ext_enddate");//ext_enddate.toISOString();
                $('#ext_enddate').val(iso_end);
            }
            if (getURLParameter("limit")) {
                limit = getURLParameter("limit");
                 $('#ext_limit').val(limit);
            }
            if(getURLParameter("ext_search_date_type")) {
                var ext_search_date_type = getURLParameter("ext_search_date_type");
                $('#ext_search_date_type').val(ext_search_date_type);
                $('input:radio[name="sip4d_search_type_radio"]').val([ext_search_date_type]);
            }
            // localeに合わせて言語を設定
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
            // Add a date-range picker widget to the <input> with id #daterange
            $('input[id="daterange_search"]').daterangepicker(
                datelocation,
            );
            $('input[id="daterange_search"]').on('apply.daterangepicker', function(ev, picker) {
                if ('ja'===lang) {
                    $(this).val(picker.startDate.format('YYYY/MM/DD') + ' - ' + picker.endDate.format('YYYY/MM/DD'));
                } else {
                    $(this).val(picker.startDate.format('MM/DD/YYYY') + ' - ' + picker.endDate.format('MM/DD/YYYY'));
                }
                start = picker.startDate.format('YYYY-MM-DDTHH:mm:ss') + 'Z';
                end = picker.endDate.format('YYYY-MM-DDTHH:mm:ss') + 'Z';
                search_type = $('input:radio[name="sip4d_search_type_radio"]:checked').val();
                console.log("ext_search_date_type:"+search_type);
                $('#ext_startdate').val(start);
                $('#ext_enddate').val(end);
                $('#ext_search_date_type').val(search_type);
                $(".search-form").submit();
            });
            $('input[id="daterange_search"]').on('cancel.daterangepicker', function(ev, picker) {
                $(this).val('');
            });
            // Returns url parameter of given name (if it exists)
            function getURLParameter(name) {
                return decodeURIComponent((new RegExp('[?|&]' + name + '=' + '([^&;]+?)(&|#|;|$)').exec(location.search)||[,""])[1].replace(/\+/g, '%20'))||null;
            }
            // イベント設定
            $('#disaster_id_update').on('click', function(e) {
                this.disabled = true;
                var result = module.updateDisasterInfo('disaster_id', module._('disaster_id'));
                if (!result)  this.disabled = false;
                return false;
            });
            $('#disaster_name_update').on('click', function(e) {
                this.disabled = true;
                var result = module.updateDisasterInfo('disaster_name',module._('disaster_name'));
                if (!result)  this.disabled = false;
                return false;
            });

            $('#harvest_flag_update').on('click', function(e) {
                this.disabled = true;
                var result = module.updateDisasterInfo('harvest_flag',module._('harvest_flag'));
                if (!result)  this.disabled = false;
                return false;
            });

            //ckeckbox
            $('#all_check').on('change', function() {
                $('input[name=dataset_ids]').prop('checked', this.checked);
            });
        },

        /**
        選択したデータセットの災害ID,災害名を一括で更新する。
         */
        updateDisasterInfo: function(type, typename)
        {
            var self = this;
            if (!confirm( this._('Update %(name)s collectively', {name: typename}) )) return false;
            var form = $('#update-disaster-form')
            var url = '/sip4d/disaster_update?type='+type+'&'+Math.random();
            if ($('input[name='+type+']').val()=='') {
                if (!confirm( this._('%(name)s value is empty. Do you want to update?', {name: typename}) )) return false;
            }
            this.showLoading(this._('Updating %(name)s', {name: typename}));
            // CSRF対策
            var csrf_value = $('meta[name=_csrf_token]').attr('content');

            let typevalue = $('[name="'+type+'"]').val();
            let dataset_ids = [];
            $('[name="dataset_ids"]:checked').each(function() {
                dataset_ids.push($(this).val());
            });
            let postdata = {};
            postdata[type] = typevalue;
            postdata['dataset_ids'] = dataset_ids;
            jQuery.ajax({
                type: 'post',
                beforeSend: function (jqXHR, settings) { {
                    if (csrf_value)
                        jqXHR.setRequestHeader('X-CSRFToken', csrf_value);
                } },
                url : url,
                data: JSON.stringify(postdata),  //form.serialize(),
                dataType : "json",
                contentType: 'application/json',
                success: function (results) {
                    console.log(results)
                    if (results.success) {
                        alert(results.mes);
                        //if ($('.loadingMsg'))$('.loadingMsg').text('');
                        location.reload();
                    } else if(results.error) {
                        alert(results.error);
                        self.removeLoading(type);
                    }
                },
                error: function () {
                    console.log("Updating error");
                    self.removeLoading(type);
                },
                complete: function () {
                    //button.prop('disabled', false).removeClass('loading');
                }
            });
            return true;
        },
        /**
        更新中に画面を操作できないようにローディング画面を表示
         */
        showLoading : function(msg)
        {
            if (typeof msg === "undefined") {
                msg = "";
            }
            var showMsg = "<div class='loadingMsg'>" + msg + "</div>";
            if($("#loading").length == 0){
                $("body").append("<div id='loading'>" + showMsg + "</div>");
            }
        },
        /**
        ローディング画面を非表示
         */
        removeLoading : function(type)
        {
            if ($("#loading")) {
                $("#loading").remove();
            }
            if ($('#'+type+'_update')) {
                $('#'+type+'_update').prop('disabled', false);
            }
        },
    }
});
