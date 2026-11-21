# Security

## Report a problem

Please do not open a public issue for a security problem. Report it privately here:

https://github.com/AlexandruGirlea/pyskins/security/advisories/new

We read every report and answer as soon as we can.

## Which version gets fixes

The newest release on [PyPI](https://pypi.org/project/pyskins/).

## Good to know

- Installing pyskins adds a small `.pth` file, so Python registers a source codec at every start-up of that interpreter. It only handles files with a `pyskins-*` coding line. The [README](https://github.com/AlexandruGirlea/pyskins#-good-to-know) says more.
- Obfuscation is not encryption. Anyone with the key file reads everything, so do not use it to protect secrets.
