var Status = (function() {
  var container = $('#status');
  function update(msg, color) {
    $('span', container).remove();
    $('<span>').addClass(color).text(msg).appendTo(container);
  }

  function update_score(wins, draws, losses) {
    var c = $('#score-status');
    $('.wins span', c).text(wins);
    $('.draws span', c).text(draws);
    $('.losses span', c).text(losses);
    $('#score-status:hidden').show();
  }

  return {
     update: update,
     update_score: update_score
  };
})();

var Hand = (function() {
  var hand;
  var discarded = [];
  var _gone = false;
  var _in_final = false;

  $('form.yourcards').submit(function() {
    _gone = true;
    $('.pickedcard').attr('disabled', 'disabled');
    Play.discard(discarded, function() {
      discarded = [];
    });
    return false;
  });

  $('#preview [name="yes"]').on('click', function() {
    Play.accept(function() {
      $('#preview').hide();
    });
  });

  $('#preview [name="no"]').on('click', function() {
    Play.refuse(function() {
      $('#preview').hide();
    });
  });

  return {
     reopen: function() {
       _gone = false;
     },
    preview: function(card) {
      $('#preview .container .card').remove();
      $('#preview p').text("Would you like to keep this card?");

      $('<button>')
           .click(function() {
             alert('not implemented');
             return false;
           })
           .val(card)
               .addClass('card').addClass('c' + card)
                 .prependTo($('#preview .container'));
      $('#preview button').show();
      $('#preview').fadeIn('slow');

    },
    previewed: function(card, player) {
      $('#preview .container .card').remove();
      $('#preview p').text(player + " is offered:");

      $('<button>')
           .click(function() {
             alert('not implemented');
             return false;
           })
           .val(card)
               .addClass('card').addClass('c' + card)
                 .prependTo($('#preview .container'));
      $('#preview button').hide();
      $('#preview').fadeIn(500);

    },
    show_hand: function(cards) {
      $('.yourcards .card').addClass('oldcard')
      $.each(cards, function(i, card) {
        var newcard = $('<button>')
          .on('click', function() {
            if (_gone || _in_final) return;
            if (this.className.search(/pickedcard/) == -1) {
              discarded.push($(this).val());
              $(this).addClass('pickedcard');
            } else {
              $(this).removeClass('pickedcard');
              discarded.splice($.inArray($(this).val(), discarded), 1);
            }
            return false;
          })
            .val(card)
                .addClass('card').addClass('c' + card);
        newcard.appendTo($('.yourcards'));
      });
      $('.yourcards .oldcard').remove();
      hand = cards;
      $('<p>')
        .append($('<span>').text(($('#log p').size() + 1) + ': ' + cards.join(', ')))
          .prependTo($('#log'));
      //$('#log').scrollTop($('#log').scrollTop() + 1000);
    },
    final_start: function() {
      $('button.card', '.yourcards').off('click');
      _in_final = true;
    },
    lay_final_card: function(card) {
      var c = $('.final .cards');
      if (!$('.you', c).size()) {
        $('<div>')
          .addClass('you').addClass('pile')
            .data('player', 'you')
            .append($('<strong>').text("You"))
              .appendTo(c);
      }
      $('.you', c)
        .append($('<button>').addClass('card').addClass('c' + card));

    },
    laid_final_card: function(card, player) {
      var c = $('.final .cards');
      var players_pile = null;
      $('div.pile', c).each(function(i, each) {
        if ($(each).data('player') == player) {
          players_pile = $(each);
        }
      });
      if (!players_pile) {
        players_pile = $('<div>')
          .addClass('opponent').addClass('pile')
            .data('player', player)
            .append($('<strong>').text(player))
              .appendTo(c);
      }
      players_pile
        .append($('<button>').addClass('card').addClass('c' + card));
    }
  }
})();


var Play = (function() {
  var _socket;
  var _ready = false;
  var _in_final = false;

  function reset_animation() {
    $("form.restart").hide();
    $(".play-icons img").not(".chosen-weapon").show();
    $(".play-icons img").removeClass('chosen-weapon');
  }

  function init(socket) {
    _socket = socket;

    $('form.restart').submit(function() {
      reset_animation();
      Status.update('Ready to play', 'green');
      Hand.reopen();
      _ready = true;
      return false;
    });

    $('form.chat').submit(function() {
      var name = $.trim($('input[name="name"]').val());
      var message = $.trim($('input[name="message"]').val());
      if (!name.length) {
        alert("No name :(");
      } else if (!message.length) {
        $('input[name="message"]').focus();
      } else {
        _socket.send_json({name: name, message: message});
        $('input[name="message"]').val('');
        $('input[name="message"]').focus();
      }
      return false;
    });


    $('form.play').submit(function() {
      alert("Apparently not Obsolete?");
      var button = $('input[type="hidden"]', this).val();
      _socket.send_json({button: button});
      Status.update('Checking...', 'orange');
      $(this).hide();
      return false;
    });
  }

  function has_logged_in(email) {
    _socket.send_json({register: email});
  }

  function set_ready(toggle) {
    _ready = toggle;
    Status.update('Ready to play', 'green');
  }

  function discard(cards, callback) {
    _socket.send_json({discard: cards});
    callback();
  }

  function refuse(callback) {
    _socket.send_json({refuse: true});
    callback()
  }

  function accept(callback) {
    _socket.send_json({accept: true});
    callback();
  }

  function final_(state) {
    _in_final = true;

    $('.final:hidden').fadeIn(500);
    $('.yourcards button.go').hide();
    if (state.status) {
      $('.status span', '.final').text(state.status);
    }
    if (state.laid) {
      L('LAID', state.laid);
      Hand.laid_final_card(state.laid.card, state.laid.player);
    }
    if (state.turn) {
      if (!state.status) {
        $('.status span', '.final').text("Your turn, pick a card");
      }
      $('.yourcards .card').off('click').on('click', function() {
        _socket.send_json({final_card: $(this).val()});
        Hand.lay_final_card($(this).val());
        $(this).fadeOut(300);
      });
    } else {
      $('.yourcards .card').off('click');
    }
  }

  return {
     init: init,
     has_logged_in: has_logged_in,
     set_ready: set_ready,
      discard: discard,
      refuse: refuse,
      accept: accept,
      final_: final_
  };

})();

SockJS.prototype.send_json = function(data) {
  this.send(JSON.stringify(data));
};

var initsock = function(callback) {
  sock = new SockJS('http://' + location.hostname + ':9999/play');

  sock.onmessage = function(e) {
    console.log('  -> message', e.data);

    if (e.data.registered) {
      $('.auth').hide();
      $('.play-icons, .chat').fadeIn(500);
      Status.update('Registered', 'black');
      $('input[name="name"]').val(e.data.registered);
    }

    if (e.data.status) {
      Status.update(e.data.status, e.data.color || 'black');
    }

    if (e.data.update_score) {
      Status.update_score(e.data.update_score.wins,
                          e.data.update_score.draws,
                          e.data.update_score.losses);
    }

    if (e.data.message) {
      $('<p>')
        .append($('<strong>').text(e.data.name + ': '))
          .append($('<time>').text(e.data.date))
            .append($('<span>').text(e.data.message))
              .appendTo($('#log'));
        $('#log').scrollTop($('#log').scrollTop() + 1000);
    }

    if (e.data.preview) {
      Hand.preview(e.data.preview);
    }

    if (e.data.previewed && e.data.player) {
      Hand.previewed(e.data.previewed, e.data.player);
    }

    if (e.data['final']) {
      Play.final_(e.data['final']);
    }

    if (e.data.hand) {
      Hand.show_hand(e.data.hand);
      Hand.reopen();
    }

    if (e.data.refused || e.data.accepted) {
      $('#preview').hide();
    }

    if (e.data.ready) {
      Play.set_ready(true);
    }


  };
  sock.onclose = function() {
    console.log('closed');
    Status.update('Disconnected', 'red');
  };
  sock.onopen = function() {
    //log('opened');
    console.log('open');
    Status.update('Connected but not logged in', 'green');
    //sock.send('test');
    if (sock.readyState !== SockJS.OPEN) {
      throw "Connection NOT open";
    }
    callback(sock);
  };
};


$(function() {
  console.log('let the madness begin!');
  initsock(function(socket) {
    Play.init(socket);
  });
});
