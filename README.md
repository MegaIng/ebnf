# ebnf tools

A collection of tools to work with ebnf grammars, like conversion between different formats, railroad generation and random example generation.

## Getting Started

### Prerequisites

Requires python3.9 or higher.

Other requirements like `lark` and `railroad-diagrams` should be installed automatically by pip

### Installing

`pip install ebnf`

If you want to use one of the extra utils with extra requirements, use the `ebnf[<extra>]` syntax:

- **railroad** diagram generation:
`pip install ebnf[railroad]`
  
## Tools

The 'base' ebnf dialect for this package the one used by the `lark` package. All features should work for it, but might not work for others.


### `ebnf.railroad` - railroad diagram generation

Generates a html file containing svg for each rule/terminal in the input grammar. Can take a lot of different options, check the help for more info

### `ebnf.convert` - dialect translation (TODO)

Attempts to convert between different dialects, with the focus being generation `lark` compatible output

### `ebnf.example` - generates an example for a grammar (TODO)

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/MegaIng/ebnf/tags). 

## Authors

* [MegaIng](https://github.com/MegaIng) - *Initial work*

See also the list of [contributors](https://github.com/MegaIng/ebnf/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

