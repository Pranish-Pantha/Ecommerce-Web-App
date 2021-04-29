function run(session_id){

var stripe = Stripe('pk_test_51IINswHHfxcLbDGFW5TzRiVYjRWES1bAM3lD84bODcURT8myP30VToH5Pl3gjmOn4A6jWd5TmVqysoqBkM87Hr4D00nh9KBgWt');

var checkoutButton = document.getElementById('checkout-button');

checkoutButton.addEventListener('click', function() {
  stripe.redirectToCheckout({
    // Make the id field from the Checkout Session creation API response
    // available to this file, so you can provide it as argument here
    // instead of the {{CHECKOUT_SESSION_ID}} placeholder.
    sessionId: session_id
  }).then(function (result) {
    // If `redirectToCheckout` fails due to a browser or network
    // error, display the localized error message to your customer
    // using `result.error.message`.
  });
});
}
