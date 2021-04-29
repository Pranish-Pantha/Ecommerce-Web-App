/**
 * Creates a new marker and adds it to a group
 * @param {H.map.Group} group       The group holding the new marker
 * @param {H.geo.Point} coordinate  The location of the marker
 * @param {String} html             Data associated with the marker
 */
function addMarkerToGroup(group, coordinate, html) {
    var marker = new H.map.Marker(coordinate);
    // add custom data to the marker
    marker.setData(html);
    group.addObject(marker);
}
function print(vendors){
console.log(vendors)
}
/**
 * Add two markers showing the position of Liverpool and Manchester City football clubs.
 * Clicking on a marker opens an infobubble which holds HTML content related to the marker.
 * @param  {H.Map} map      A HERE Map instance within the application
 */
function addInfoBubble(map, vendors) {
    var group = new H.map.Group();

    map.addObject(group);

    // add 'tap' event listener, that opens info bubble, to the group
    group.addEventListener('tap', function (evt) {
        // event target is the marker itself, group is a parent event target
        // for all objects that it contains
        var bubble = new H.ui.InfoBubble(evt.target.getGeometry(), {
            // read custom data

            content: evt.target.getData()
        });
	
        // window.location.href = "./new";
        // show info bubble
	
        ui.addBubble(bubble);
    }, false);

	for(var i = 0; i <vendors.length; i++)
	{
    addMarkerToGroup(group, { lat: vendors[i]['latitude'], lng: vendors[i]['longitude'] },
        `<div><a href="/${vendors[i]['vendor_name']}">${vendors[i]['vendor_name']}</a>` +
        `</div><div>${vendors[i]['location']}</div>`);

}

}
/**
 * Boilerplate map initialization code starts below:
 */
// initialize communication with the platform
// In your own code, replace variable window.apikey with your own apikey


var platform, defaultLayers, map, behavior, ui;

// Now use the map as required...
function start(vendors){
console.log("ran")
platform = new H.service.Platform({
    apikey: "" //Add in your HERE API key
});
defaultLayers = platform.createDefaultLayers();
map = new H.Map(document.getElementById('map'),
    defaultLayers.vector.normal.map, {
    center: { lat: 36.0, lng: -79.0 },
    zoom: 7,
    pixelRatio: window.devicePixelRatio || 1
});
window.addEventListener('resize', () => map.getViewPort().resize());
behavior = new H.mapevents.Behavior(new H.mapevents.MapEvents(map));
ui = H.ui.UI.createDefault(map, defaultLayers);
addInfoBubble(map, vendors);
}
function update(vendors){
console.log(vendors)
ui.getBubbles().forEach(bub => ui.removeBubble(bub));
addInfoBubble(map, vendors);
}
