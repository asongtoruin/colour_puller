import colorsys
from io import BytesIO
import os
import requests

import numpy as np
from PIL import Image, ImageDraw
from scipy.cluster.vq import whiten
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


class SpotifyAlbum:
    def __init__(self, resp_dict, from_api=True):
        self.name = resp_dict.get('name', None)
        self.release_date = resp_dict.get('release_date', 'Unknown')
        self.id = resp_dict.get('id', None)

        if from_api:
            # Handle possibility of many artists
            artists = resp_dict['artists']
            if len(artists) > 5:
                self.artists = 'Various'
            else:
                self.artists = ', '.join(
                    art.get('name', 'Unknown') for art in artists
                )
            
            urls = resp_dict.get('external_urls', {'spotify': None})
            self.link = urls['spotify']
            
            # Get the largest version of the album artwork
            images = resp_dict.get('images', [{'url': None, 'height': 0}])
            images.sort(key=lambda x: x['height'], reverse=True)
            self.art_link = images[0]['url']
        else:
            self.artists = resp_dict.get('artists', 'Unknown')
            self.link = resp_dict.get('link', None)
            self.art_link = resp_dict.get('art_link', None)
        
        self.album_art = None
        self.album_palette = None
    
    def __str__(self):
        return (
            f'Album Name: {self.name}\n'
            f'Artist(s): {self.artists}\n'
            f'Released: {self.release_date}\n'
            f'Link: {self.link}'
        )
    
    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return NotImplemented
    
    def to_dict(self):
        return self.__dict__

    def get_images(self, get_kwargs=None, draw_kwargs=None):
        if not get_kwargs:
            get_kwargs = dict()

        if not draw_kwargs:
            draw_kwargs = dict()
        
        self.album_art = AlbumArtwork(self.art_link, source_type='url')
        self.album_art.get_palettes(**get_kwargs)
        self.album_palette = self.album_art._chosen_palette
        drawn, palette = self.album_art.draw_palette_on_image(**draw_kwargs)

        return self.album_art.path, drawn, palette


class AlbumArtwork:
    original_folder = 'artwork_downloads'
    edited_folder = 'artwork_edited'
    palette_folder = 'artwork_palette'
    for f in (original_folder, edited_folder, palette_folder):
        if not os.path.isdir(f):
            os.mkdir(f)

    def __init__(self, source, source_type='url', name=None):
        if source_type.lower() == 'file':
            self._original_image = Image.open(source)
            self.path = source
        elif source_type.lower() == 'url':
            resp = requests.get(source)
            if name is None:
                new_name = source.split('/')[-1] + '.jpeg'
            else:
                new_name = name + '.jpeg'
            self.path = os.path.join(__class__.original_folder, new_name)
            with open(self.path, 'wb') as disk_file:
                disk_file.write(resp.content)
            
            self._original_image = Image.open(BytesIO(resp.content))
        
        self._file_name  = os.path.basename(self.path)
        self._palettes = None
        self._chosen_palette = None

    def get_palettes(self, resize_pix=150, min_colours=2, max_colours=15, 
                     apply_whiten=True, match_actual=True,
                     threshold=0.05, thresh_mode='additive'):
        if not self._palettes:
            self._palettes = PaletteSet()
        
        # Scale down image size for faster running
        resized = self._original_image.resize((resize_pix, resize_pix))
        rgb = np.array(resized.getdata())
        if apply_whiten:
            red_std = rgb.T[0].std()
            grn_std = rgb.T[1].std()
            blu_std = rgb.T[2].std()

            rgb = np.array([whiten(c) for c in rgb.T]).T

        for k in range(min_colours, max_colours):
            km = KMeans(n_clusters=k, n_init=20, random_state=1234).fit(rgb)
            labels = km.labels_

            score = silhouette_score(rgb, labels, metric='euclidean')
            colours = km.cluster_centers_

            if match_actual:
                tf = km.transform(rgb)
                closest_ind = [
                    np.argsort(tf[:,i])[0] for i in range(len(colours))
                ]
                colours = [
                    (rgb[ind][0], rgb[ind][1], rgb[ind][2]) 
                    for ind in closest_ind
                ]
            
            if apply_whiten:
                colours = [
                    (int(c[0] * red_std), int(c[1] * grn_std), int(c[2] * blu_std))
                    for c in colours
                ]
            
            self._palettes.add(Palette(colours, score))

        self._chosen_palette = self._palettes.pick(threshold, thresh_mode)

    def draw_palette_on_image(self, shape='circle', buffer_prop=0.05):
        if not self._palettes:
            raise ValueError(
                'No palettes available. Ensure get_palettes is run first.'
            )
        
        # First, save the palette to an image file
        pal_path = os.path.join(__class__.palette_folder, self._file_name)
        self._chosen_palette.plot(save_path=pal_path)

        h, w = self._original_image.size

        new_image = Image.new(mode='RGBA', size=(h, w))
        new_image.paste(self._original_image.convert('L'))
        
        big_h = h * 5
        big_w = w * 5
        
        bigger = Image.new('RGBA', (big_h, big_w))
        
        draw = ImageDraw.Draw(bigger)

        if shape == 'circle':
            shape = draw.ellipse
        elif shape == 'square':
            shape = draw.rectangle

        shape_size = int(big_w / len(self._chosen_palette.colours)) + 1
        buffer_val = shape_size * buffer_prop
        
        row_top = (big_h / 2) + (shape_size / 2)
        row_bottom = row_top - shape_size

        for i, colour in enumerate(self._chosen_palette.colours):
            scaled_colour = [p / 255 for p in colour]
            outline = (
                'black' if colorsys.rgb_to_hls(*scaled_colour)[1] > .5
                else 'white'
            )
            
            shape(
                [
                    i*shape_size+buffer_val, row_bottom+buffer_val,
                    (i+1)*shape_size-buffer_val,row_top-buffer_val
                ],
                fill=colour, outline=outline
            )

        bigger = bigger.resize((h, w), Image.ANTIALIAS)
        new_image.paste(bigger, mask=bigger)
        new_image = new_image.convert('RGB')

        new_path = os.path.join(__class__.edited_folder, self._file_name)

        new_image.save(new_path, quality=100, subsampling=0)
        
        return new_path, pal_path


class Palette:
    def __init__(self, colours, score=0):
        self.colours = colours
        self.colour_count = len(colours)
        self.score = score
        self.sort()
    
    @property
    def mpl_colours(self):
        return [(r/255, g/255, b/255) for r, g, b in self.colours]

    @property
    def hex_colours(self):
        return ['#{:02x}{:02x}{:02x}'.format(*c) for c in self.colours]
    
    def sort(self, space='hsv'):
        conversions = {
            'rgb': lambda x: x,
            'hsv': lambda x: colorsys.rgb_to_hsv(*x),
            'hls': lambda x: colorsys.rgb_to_hls(*x),
            'yiq': lambda x: colorsys.rgb_to_yiq(*x),
        }

        self.colours = sorted(self.colours, key=lambda x: conversions[space](x))
        return self.colours
    
    def plot(self, save_path=None, ax=None):
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        import seaborn as sns
    
        n = len(self.colours)

        if ax:
            no_ax = False
        else:
            no_ax = True
            fig, ax = plt.subplots(1, 1, figsize=(n, 1))

        ax.imshow(np.arange(n).reshape(1, n),
                  cmap=mpl.colors.ListedColormap(self.mpl_colours),
                  interpolation="nearest")# , aspect="auto")
        ax.set_xticks(np.arange(n) - .5)
        ax.set_yticks([-.5, .5])

        if no_ax:
            fig.subplots_adjust(
                left=0, right=1, bottom=0, top=1, hspace=0, wspace=0
            )
            ax.axis('off')
        else:
            ax.set_aspect('equal')

        if save_path:
            plt.savefig(save_path, bbox_to_inches='tight', pad_inches=0)

        return ax


class PaletteSet:
    def __init__(self):
        self._palette_set = set()
    
    def add(self, pal: Palette):
        self._palette_set.add(pal)

    def pick(self, threshold=0.05, thresh_mode='additive'):
        top_scoring = sorted(self._palette_set, key=lambda p: p.score)[-1]
        if thresh_mode:
            if thresh_mode == 'additive':
                candidates = set(
                    pal for pal in self._palette_set 
                    if pal.score >= top_scoring.score - threshold
                )
            else:
                candidates = set(
                    pal for pal in self._palette_set 
                    if pal.score >= top_scoring.score * (1 - threshold)
                )

            return sorted(candidates, key=lambda p: p.colour_count)[-1]

if __name__ == '__main__':
    pal = Palette(colours=[(255,255,255), (240,248,255), (245,245,245)])
    print(pal.hex_colours)
