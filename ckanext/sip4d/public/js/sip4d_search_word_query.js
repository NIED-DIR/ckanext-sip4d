this.ckan.module('sip4d_search_word_query', function ($, _) {
    return {
        options: {
            //　検索文字取得要素名
            base_input_name : null,
            // 検索フィールド名取得要素名
            base_select_name : null,
            // 検索文字追加要素名
            target_input_name : null,
            // 検索時に-を追加して除外指定
            search_except : false
        },
        initialize: function() {
            var module = this;
            module.options.base_input_name = this.el.data('inputname');
            module.options.base_select_name = this.el.data('selectname');
            module.options.target_input_name = this.el.data('targetname');

            if (this.el.data('except') && this.el.data('except') == 'true') {
                this.options.search_except = true;
            }

            var entityMap = {
              '&': '&amp;',
              '<': '&lt;',
              '>': '&gt;',
              '"': '&quot;',
              "'": '&#39;',
              '/': '&#x2F;',
              '`': '&#x60;',
              '=': '&#x3D;',
              ":": ''
            };
            function escapeHtml (string) {
              return String(string).replace(/[&<>"'`=\/:]/g, function (s) {
                return entityMap[s];
              });
            }
            $(this.el).on('click', function(){
                const base_input = $('input[name="'+module.options.base_input_name+'"]');
                const base_select = $('select[name="'+module.options.base_select_name+'"]');
                const target_input = $('input[name="'+module.options.target_input_name+'"]');
                if (!base_input) {
                    alert(module._('Unable to retrieve search string'));
                    return;
                }
                if (!base_select) {
                    alert(module._('Unable to retrieve search field'));
                    return;
                }
                if (!target_input) {
                    alert(module._('Target to add search string not found'));
                    return;
                }
                // 検索文字列を分割
                let search_string = base_input.val();
                let search_string_list = [];
                if (search_string) {
                    search_string = search_string.replaceAll("　"," "); //空白を半角に変換
                    //記号の除去
                    search_string = escapeHtml(search_string);
                    if (search_string.indexOf(' ') != -1) {
                        search_string_list = search_string.split(' ');
                    } else {
                        search_string_list.push(search_string);
                    }
                }
                // 検索対象フィールド
                let search_keyword = base_select.val();
                //追加する検索文字列
                let add_search_word = "";
                $.each(search_string_list, function(idx, str){
                    let word = "";
                    if (module.options.search_except) {
                        word += "-";
                    }
                    word += search_keyword + ":" + str;
                    if (add_search_word.length > 0) {
                        add_search_word += " ";
                    }
                    add_search_word += word;
                });
                // 検索文字列取得
                let base_search_word = target_input.val();
                base_search_word = escapeHtml(base_search_word);
                base_search_word += " " + add_search_word;
                if (base_search_word) {
                    target_input.val(base_search_word);
                }
            });
        },
    }
});