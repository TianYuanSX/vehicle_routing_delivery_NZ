# Wellington example data

This scenario is synthetic demand routed between real public-facing Wellington
locations. It contains no customer or personal data. Order sizes, creation times,
service times, and priorities are invented for demonstration purposes.

## Address and coordinate method

Street addresses were checked against the organisations' public pages on
2026-07-29. Latitude and longitude were then generated from the complete address
or named public location using the OpenStreetMap Nominatim search service. The
returned coordinates are stored in the CSV so the built-in example remains fully
offline and reproducible.

Coordinates are representative delivery/map points, not guaranteed loading-bay
entrances. Re-geocode and operationally verify them before real dispatch use.

## Public address sources

- Depot — NZ Post Wellington Super Depot, `8 Carmel Terrace`: address supplied for
  this example and corroborated by an NZ Post recruitment location listing.
- New World Churton Park — [New World store page](https://www.newworld.co.nz/lower-north-island/wellington/churton-park)
- Woolworths Johnsonville — [Woolworths premises licence](https://www.woolworths.co.nz/content/CDJohnsonville.pdf)
- New World Karori — [New World store page](https://www.newworld.co.nz/lower-north-island/wellington/karori)
- Wētā Workshop Experiences — [Wētā Workshop Wellington](https://www.wetaworkshop.com/tours/wellington)
- PAK'nSAVE Kilbirnie — [PAK'nSAVE store page](https://www.paknsave.co.nz/lower-north-island/wellington/kilbirnie)
- New World Island Bay — [New World store page](https://www.newworld.co.nz/lower-north-island/wellington/island-bay)
  and [Snapper location listing](https://www.snapper.co.nz/locations/new-world-island-bay/)
  for the street number.
- Museum of New Zealand Te Papa Tongarewa — [Te Papa visit page](https://www.tepapa.govt.nz/visit/plan-your-visit)
- Ministry of Health — [Ministry contact page](https://www.health.govt.nz/about-us/contact-us)
- Archives New Zealand — [Wellington repository page](https://collections.archives.govt.nz/web/arena/-/wellington-repository)
- Wellington City Council — [Council contact information](https://www.letstalk.wellington.govt.nz/supporting-information)

Geocoding data is © OpenStreetMap contributors and is used under the
[Open Database License](https://www.openstreetmap.org/copyright).
