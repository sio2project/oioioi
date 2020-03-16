(function($) {
    'use strict';
    class FilterCollapse {
        constructor(filterElement) {
            this.init(filterElement);
            this.bindHover();
            this.bindToggle();
        }

        init(filterElement) {
            this.$filterElement = $(filterElement);
            this.$filterList = this.$filterElement.next('ul').hide();
        }

        bindToggle() {
            let that = this;
            this.$filterElement.click(function(){
                that.$filterList.slideToggle();
            });
        }

        bindHover() {
            this.$filterElement.css('cursor', 'pointer');
        }
    }

    $(document).ready(function() {
        $('#changelist-filter').children('h3').each(function() {
            // Initialization binds on click function to elements
            new FilterCollapse(this);
        });
    });
})(django.jQuery);