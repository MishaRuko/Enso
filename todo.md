- [ ] Floor plan to 3D model
      Convert floor plan image to 3D model using existing pipeline as context.

Frontend react or vue
Backend must be dockerised

Assignees: Misha and Danila

- [ ] Figure out furniture placement
      Use some paper as base or something. Includes possible generation of required furniture list.

Assignees: Misha and Danila

- [ ] Furniture site scraping
      Use IKEA API or just scrape. Get important info including:
- Images of furniture
- Dimensions
- Description
- Price
- Buy link
- Eco friendliness info

Assignees: Charlene

- [ ] User interaction agent
      Agent that interacts with the user. Use ElevenLabs as voice agent that will run all the stuff.
      Includes Miro integration.
      Multi-modal - takes reference images as input.

Assignees: Lara

- [ ] Website
      Nice website to view everything.
      Includes stripe integration.
      3D visualisation with interactivity

Assignees: Claude

- [ ] Presentation
      Assignees: Danila

Pipeline:

- [ ] User uploads floor plan. An empty home model is generated in the background.
- [ ] User joins a call/voice chat with ElevenLabs
- [ ] Agent interviews user to get important info: budget, desired style, etc… and creates miro board live.
- [ ] Agent ends call and starts processing
- [ ] Come up with furniture spec: list of furniture items, dimensions, placement, etc…
- [ ] Search ikea for required furniture and collect necessary data
- [ ] Use scraped data to add new items to library by generating 3D models
- [ ] Do furniture placement and building final 3D model
- [ ] Show user final design. Allow user to move stuff/choose furniture options
- [ ] Export mood book, can use nano banana
- [ ] Allow user to order stuff using stripe
