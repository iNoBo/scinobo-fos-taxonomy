FROM mcr.microsoft.com/devcontainers/python:3.11

# Install additional packages
RUN chmod 1777 /tmp && \
    apt-get update && \
    apt-get install -y curl unzip && \
    rm -rf /var/lib/apt/lists/*


# Install SDKMAN
RUN curl -s "https://get.sdkman.io" | bash

# Source SDKMAN and install Spark
RUN bash -c "source /root/.sdkman/bin/sdkman-init.sh && sdk install spark && sdk install java 21.0.5-tem"

# Add Spark binaries to PATH
# Set JAVA_HOME environment variable
ENV JAVA_HOME="/root/.sdkman/candidates/java/current"
ENV PATH="${JAVA_HOME}/bin:${PATH}:/root/.sdkman/candidates/spark/current/bin"
# ENV PATH="/root/.sdkman/candidates/spark/current/bin:${PATH}"

WORKDIR /app

# Copy only the requirements file, to cache the installation of dependencies
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the rest of your application
COPY . /app

# Set default command
CMD ["bash"]